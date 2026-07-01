import re
import json
from typing import List

ROLE_USER_RE = re.compile(r"^\s*(?:\*\*\s*)?user\b[:\-]?", re.I)
ROLE_ASSISTANT_RE = re.compile(r"^\s*(?:\*\*\s*)?(?:assistant|agent)\b[:\-]?", re.I)

def parse_trace_lines(lines: List[str]):
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
        line = raw.rstrip('\n')
        if not line.strip():
            if cur_buf:
                cur_buf.append('')
            continue

        if ROLE_USER_RE.match(line):
            flush()
            cur_role = "user"
            content = ROLE_USER_RE.sub('', line).strip()
            if content:
                cur_buf = [content]
            else:
                cur_buf = []
            continue

        if ROLE_ASSISTANT_RE.match(line):
            flush()
            cur_role = "assistant"
            content = ROLE_ASSISTANT_RE.sub('', line).strip()
            if content:
                cur_buf = [content]
            else:
                cur_buf = []
            continue

        if line.lstrip().startswith('>'):
            content = line.lstrip()[1:].lstrip()
            cur_buf.append(content)
            continue

        if cur_role:
            cur_buf.append(line)
        else:
            if line.strip().lower().startswith('turn'):
                continue
            cur_role = 'user'
            cur_buf = [line]

    flush()
    return messages


def convert_text_to_messages(text: str):
    try:
        j = json.loads(text)
        if isinstance(j, dict) and 'messages' in j:
            return j['messages']
    except Exception:
        pass

    lines = text.splitlines()
    return parse_trace_lines(lines)


def convert_file_to_json(path):
    txt = open(path, 'r', encoding='utf-8').read()
    msgs = convert_text_to_messages(txt)
    return {"messages": msgs}
