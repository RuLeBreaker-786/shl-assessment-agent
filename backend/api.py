import io
import json
from fastapi import FastAPI, File, UploadFile, status

from backend.schemas import ChatRequest, ChatResponse, Recommendation
import backend.rag as rag
from backend.parser import get_grounding_context, parse_refuse_request, parse_explicit_request
from backend.agent import SYSTEM_PROMPT, infer_local_recommendations, local_catalog_search

app = FastAPI()

# Make sure we load the catalog into memory the moment the script is imported
rag.load_catalog_data()

@app.on_event("startup")
async def startup_event():
    # Double-checking the database is loaded when the server officially starts listening.
    rag.load_catalog_data()

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest):
    # The main brain of the operation. This takes the chat history, figures out what to do, and replies.
    
    # We cap the conversation at 7 turns so they don't wander off topic forever.
    current_turns = len(payload.messages)
    force_closure = current_turns >= 7

    # Flatten the chat to a single string so our search engine can grab relevant info.
    conversation_history_str = "\n".join([f"{m.role}: {f'{m.content}'}" for m in payload.messages])
    grounding_data = get_grounding_context(conversation_history_str)

    # Prep the prompt for Groq, injecting the strict rules and our search results.
    groq_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if grounding_data:
        groq_messages.append({"role": "system", "content": f"Grounding Context from SHL Catalog:\n{grounding_data}"})
        
    for m in payload.messages:
        groq_messages.append({"role": m.role, "content": m.content})

    try:
        # Check if we need to refuse the prompt entirely (like if they asked a legal question).
        if parse_refuse_request(conversation_history_str):
            return ChatResponse(
                reply="I cannot provide legal advice. I can only recommend SHL assessments for hiring and development.",
                recommendations=[],
                end_of_conversation=False,
            )

        # If we have no API key, use the local backup search instead.
        if rag.groq_client is None:
            return infer_local_recommendations(payload.messages)

        # The actual API call to the LLM, asking for a structured JSON response.
        chat_completion = rag.groq_client.chat.completions.create(
            messages=groq_messages,
            model="llama3-70b-8192",
            response_format={"type": "json_object"},
            temperature=0.1,
            timeout=15.0
        )
        
        decision = json.loads(chat_completion.choices[0].message.content)
        
        intent = decision.get("intent", "clarify")
        reply_text = decision.get("reply", "")
        keywords = decision.get("search_keywords", [])
        job_level = decision.get("job_level", None)
        end_conv = decision.get("end_of_conversation", False) or force_closure

        # A manual override: if the LLM tried to recommend something without enough info, we force it to ask for clarity.
        explicit, explicit_keywords, explicit_job_level = parse_explicit_request(conversation_history_str)
        if intent == "recommend" and not explicit:
            intent = "clarify"
            reply_text = "I need a bit more detail to recommend the right assessment. What role, seniority, or competency are you hiring for?"
            keywords = []
            job_level = None
            end_conv = False

        if explicit_keywords:
            keywords = explicit_keywords
        if explicit_job_level:
            job_level = explicit_job_level

        recommendations_out = []

        # If the LLM decided it's time to recommend (or we hit the turn limit), we run the search.
        if intent == "recommend" or force_closure:
            if not keywords and payload.messages:
                keywords = payload.messages[-1].content.split()
                
            raw_matches = local_catalog_search(keywords, job_level)
            for rm in raw_matches:
                recommendations_out.append(
                    Recommendation(name=rm["name"], url=rm["url"], test_type=rm["test_type"])
                )
                
            if intent == "recommend" and not force_closure:
                end_conv = True

        return ChatResponse(
            reply=reply_text,
            recommendations=recommendations_out,
            end_of_conversation=end_conv
        )

    except Exception as e:
        # If absolutely anything crashes, just fail gracefully back to the local hardcoded engine.
        print(f"Exception triggered during turn processing execution: {e}")
        return infer_local_recommendations(payload.messages)

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    # A simple endpoint so hosting services like Render know the app hasn't crashed.
    return {"status": "ok"}

@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    # A friendly greeting for anyone poking at the base URL.
    return {"status": "ok", "message": "SHL assessment agent is running. Use /chat or /health."}

@app.post('/ingest')
async def ingest_trace(file: UploadFile = File(...)):
    # Cracks open a file the user uploaded (PDF, DOCX, text) and rips the text out so the chat can read it.
    try:
        content = await file.read()
        text = ""
        filename = (file.filename or "").lower()
        content_type = (file.content_type or "").lower()

        if content_type == "application/pdf" or filename.endswith(".pdf"):
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(io.BytesIO(content))
                text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
                if not text.strip():
                    return {"error": "PDF uploaded but text extraction returned empty content. Please use a text or markdown file if possible."}
            except ImportError:
                return {"error": "PDF upload requires PyPDF2. Install it with `pip install PyPDF2` or upload a text-based file."}
            except Exception as e:
                return {"error": f"PDF extraction failed: {e}"}
        elif filename.endswith(".docx") or content_type in ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",):
            try:
                from docx import Document
                doc = Document(io.BytesIO(content))
                text = "\n\n".join(p.text for p in doc.paragraphs if p.text)
                if not text.strip():
                    return {"error": "DOCX uploaded but text extraction returned empty content. Please upload a text-based file."}
            except ImportError:
                return {"error": "DOCX upload requires python-docx. Install it with `pip install python-docx` or upload a text-based file."}
            except Exception as e:
                return {"error": f"DOCX extraction failed: {e}"}
        else:
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    text = content.decode("cp1252")
                except UnicodeDecodeError:
                    try:
                        text = content.decode("latin-1")
                    except UnicodeDecodeError:
                        return {"error": "Could not decode uploaded file as text. Please upload plain text, markdown, JSON, or PDF."}

        if not text.strip():
            return {"error": "Uploaded file contained no readable text."}
    except Exception as e:
        return {"error": f"Could not read uploaded file: {e}"}

    try:
        from trace_converter import convert_text_to_messages
    except Exception as e:
        return {"error": f"Trace converter unavailable: {e}"}

    messages = convert_text_to_messages(text)
    return {"messages": messages}
