from typing import List, Optional
import backend.rag as rag
from backend.schemas import Message

def get_grounding_context(user_history: str) -> str:
    # Takes the user's chat, finds the top 8 matching tests, and formats them so our LLM can read them easily.
    matches = rag.retrieve_relevant_items(user_history, top_k=8)
    context_items = []
    for match in matches:
        for item in rag.CATALOG:
            if item.get("name") != match.get("name"):
                continue
            context_items.append(
                f"Name: {item.get('name')}\n"
                f"Description: {item.get('description')}\n"
                f"Keys: {item.get('keys', [])}\n"
                f"Job Levels: {item.get('job_levels', [])}\n"
                f"Link: {item.get('link')}\n---"
            )
            break
    return "\n".join(context_items[:8])

def parse_explicit_request(text: str) -> tuple[bool, List[str], Optional[str]]:
    # Plays detective to see if the user specifically asked for a certain role or skill level in their message.
    text = text.lower()
    explicit_keywords = []
    job_level = None

    level_terms = ["executive", "director", "manager", "senior", "lead", "supervisor", "vp", "vice president", "chief", "c-suite", "team lead"]
    domain_terms = ["personality", "leadership", "behavior", "sales", "marketing", "software", "engineering", "accounting", "finance", "operations", "data", "analytics", "ux", "design", "customer", "product", "legal", "hr", "human resources"]

    for term in level_terms:
        if term in text:
            job_level = "Manager" if term in ["manager", "lead", "senior", "supervisor", "team lead"] else term.capitalize()
            explicit_keywords.append(term)
            break

    for term in domain_terms:
        if term in text:
            explicit_keywords.append(term)

    if "personality" in text or "leadership" in text:
        explicit_keywords.extend(["personality", "leadership"])

    explicit_keywords = list(dict.fromkeys(explicit_keywords))
    explicit = bool(explicit_keywords or job_level)
    return explicit, explicit_keywords, job_level

def parse_refuse_request(text: str) -> bool:
    # A quick guardrail to catch if someone is asking for legal advice so we can shut it down gracefully.
    text = text.lower()
    legal_advice_terms = ["legal advice", "terminate", "termination", "employee contract", "employment contract", "wrongful termination", "dismissal", "lawyer", "lawsuit", "court"]
    legal_context_terms = ["legal", "contract", "employee", "employment", "uk", "britain", "british"]

    if any(term in text for term in legal_advice_terms) and any(term in text for term in legal_context_terms):
        return True
    if "can you give me legal advice" in text or "legal advice" in text:
        return True
    return False

def is_resume_section_message(content: str) -> bool:
    # Looks at the first line of a message to guess if it's a piece of a resume (like 'Skills' or 'Work Experience').
    if not content:
        return False
    first_line = content.splitlines()[0].strip().lower()
    return any(keyword in first_line for keyword in [
        "professional summary", "summary", "profile", "about", "overview",
        "experience", "work experience", "professional experience",
        "employment history", "education", "academic background",
        "skills", "technical skills", "competencies", "certifications",
        "licenses", "projects", "achievements", "leadership",
        "leadership experience", "training", "publications",
        "languages", "interests", "objective", "career objective",
        "volunteer experience", "professional development",
        "additional information", "core competencies", "areas of expertise",
    ])

def extract_resume_sections(messages: List[Message]) -> List[Message]:
    # Filters the whole chat history and pulls out ONLY the messages that look like resume chunks.
    return [m for m in messages if m.role == "user" and is_resume_section_message(m.content)]

def get_last_user_query(messages: List[Message]) -> str:
    # Finds the last thing the user actually asked, skipping over any massive resume uploads.
    non_resume = [m.content for m in messages if m.role == "user" and not is_resume_section_message(m.content)]
    return non_resume[-1].strip() if non_resume else (messages[-1].content.strip() if messages else "")

def build_resume_search_text(resume_sections: List[Message], query_text: str) -> str:
    # Glues the user's question and relevant resume chunks together so we can feed it into the search engine.
    query_lower = query_text.lower() if query_text else ""
    selected_sections = []

    for section in resume_sections:
        title_line = section.content.splitlines()[0].strip().lower()
        if title_line and any(word in query_lower for word in title_line.split()):
            selected_sections.append(section.content)
            continue

        if any(term in query_lower for term in ["resume", "candidate", "cv", "profile", "applicant", "uploaded"]):
            selected_sections.append(section.content)

    if not selected_sections:
        selected_sections = [section.content for section in resume_sections if section.content.strip()]

    selected_text = "\n\n".join(selected_sections)
    return f"{query_text}\n\n{selected_text}" if query_text else selected_text
