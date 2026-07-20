import re
import json
from typing import List, Optional

# A few regex patterns and keywords to help the app recognize who is talking in a chat log,
# or to spot standard resume sections like "Education" or "Work Experience".
ROLE_USER_RE = re.compile(r"^\s*(?:\*\*\s*)?user\b[:\-]?", re.I)
ROLE_ASSISTANT_RE = re.compile(r"^\s*(?:\*\*\s*)?(?:assistant|agent)\b[:\-]?", re.I)
SECTION_HEADER_RE = re.compile(r"^\s*(?:#{1,6}\s*)?(?P<header>[A-Za-z][A-Za-z0-9 &/\-]{1,100})\s*[:\-\–]?\s*$")
RESUME_SECTION_KEYWORDS = {
    "professional summary",
    "summary",
    "profile",
    "about",
    "overview",
    "experience",
    "work experience",
    "professional experience",
    "employment history",
    "education",
    "academic background",
    "skills",
    "technical skills",
    "competencies",
    "certifications",
    "licenses",
    "projects",
    "achievements",
    "leadership",
    "leadership experience",
    "training",
    "publications",
    "languages",
    "interests",
    "objective",
    "career objective",
    "volunteer experience",
    "professional development",
    "additional information",
    "core competencies",
    "areas of expertise",
}


def normalize_section_title(title: str) -> str:
    # Cleans up messy section titles so they look nice and uniform 
    # (like turning "WORK--EXPERIENCE" into "Work Experience").
    title = title.strip()
    title = re.sub(r"[\s\-_]+", " ", title)
    return title.title()


def is_resume_section_header(line: str) -> Optional[str]:
    # Checks a single line of text to see if it looks like a resume header 
    # based on our keyword list above. If it's too long, we ignore it.
    if not line or len(line.strip()) > 80:
        return None

    match = SECTION_HEADER_RE.match(line)
    if not match:
        return None

    header = match.group("header").strip()
    lower_header = header.lower()
    if any(keyword in lower_header for keyword in RESUME_SECTION_KEYWORDS):
        return normalize_section_title(header)
    return None


def parse_resume_sections(text: str) -> List[dict]:
    # Reads through a whole document line by line, chopping it up into distinct 
    # resume sections based on the headers it finds. It also catches any intro text.
    lines = text.splitlines()
    sections = []
    current_title = None
    current_lines: List[str] = []
    preamble: List[str] = []
    found_heading = False

    for raw_line in lines:
        line = raw_line.rstrip()
        heading = is_resume_section_header(line)

        if heading:
            found_heading = True
            if current_title is not None and current_lines:
                section_content = "\n".join(current_lines).strip()
                if section_content:
                    sections.append({"role": "user", "content": f"{current_title}\n{section_content}"})
            elif current_title is None and current_lines:
                preamble = current_lines

            current_title = heading
            current_lines = []
            continue

        if current_title is None:
            current_lines.append(line)
        else:
            current_lines.append(line)

    if current_title is not None and current_lines:
        section_content = "\n".join(current_lines).strip()
        if section_content:
            sections.append({"role": "user", "content": f"{current_title}\n{section_content}"})

    if found_heading and preamble:
        summary_text = "\n".join(preamble).strip()
        if summary_text:
            sections.insert(0, {"role": "user", "content": f"Summary\n{summary_text}"})

    return sections


def extract_resume_sections(text: str) -> List[dict]:
    # Takes the raw sections we found earlier and repackages them into a neat 
    # dictionary format so it's easier for the rest of the app to pull out just the title or body.
    section_messages = parse_resume_sections(text)
    structured_sections = []
    for msg in section_messages:
        lines = msg["content"].splitlines()
        if lines:
            title = lines[0].strip()
            body = "\n".join(lines[1:]).strip()
        else:
            title = "Section"
            body = ""

        structured_sections.append(
            {
                "title": title,
                "content": body,
                "message": msg,
            }
        )
    return structured_sections


def parse_trace_lines(lines: List[str]):
    # Reads a raw chat transcript and figures out who is talking ('user' vs 'assistant'), 
    # bundling their text into separate message bubbles.
    messages = []
    cur_role = None
    cur_buf = []

    def flush():
        nonlocal cur_role, cur_buf
        if cur_role and cur_buf:
            content = "\n".join([l.rstrip() for l in cur_buf]).strip()
            if content:
                messages.append({"role": cur_role, "content": content})
        cur_role = None
        cur_buf = []

    for raw in lines:
        line = raw.rstrip("\n")
        if not line.strip():
            if cur_buf:
                cur_buf.append("")
            continue

        if ROLE_USER_RE.match(line):
            flush()
            cur_role = "user"
            content = ROLE_USER_RE.sub("", line).strip()
            cur_buf = [content] if content else []
            continue

        if ROLE_ASSISTANT_RE.match(line):
            flush()
            cur_role = "assistant"
            content = ROLE_ASSISTANT_RE.sub("", line).strip()
            cur_buf = [content] if content else []
            continue

        if line.lstrip().startswith(">"):
            content = line.lstrip()[1:].lstrip()
            cur_buf.append(content)
            continue

        if cur_role:
            cur_buf.append(line)
        else:
            if line.strip().lower().startswith("turn"):
                continue
            cur_role = "user"
            cur_buf = [line]

    flush()
    return messages


def convert_text_to_messages(text: str):
    # The main traffic cop of this file. It checks if the text is already JSON, 
    # then sees if it looks like a resume, and if all else fails, treats it as a chat log.
    try:
        j = json.loads(text)
        if isinstance(j, dict) and "messages" in j:
            return j["messages"]
    except Exception:
        pass

    resume_sections = parse_resume_sections(text)
    if resume_sections:
        return resume_sections

    lines = text.splitlines()
    return parse_trace_lines(lines)


def convert_file_to_json(path):
    # A handy little helper that opens a file on your computer, runs our conversion 
    # logic on it, and packages the result into a clean JSON object.
    txt = open(path, "r", encoding="utf-8").read()
    msgs = convert_text_to_messages(txt)
    return {"messages": msgs}
