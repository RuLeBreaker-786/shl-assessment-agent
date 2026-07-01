#!/usr/bin/env python3
"""
Test runner: POST a converted trace JSON to the local /chat endpoint.
If the HTTP endpoint is unreachable, falls back to calling the local inference function
`infer_local_recommendations` from `main.py` so you can test behavior without running the server.

Usage:
  python scripts/test_post_trace.py converted_trace.json
"""
import sys
import json
import requests
from pathlib import Path

# Ensure repository root is on sys.path so we can import `main` when this script
# is executed from the `scripts/` folder.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

def fallback_run(payload):
    # Lazy import to avoid requiring server dependencies when not needed
    try:
        from main import infer_local_recommendations, Message
    except Exception as e:
        print('Fallback unavailable:', e)
        return

    msgs = [Message(role=m['role'], content=m['content']) for m in payload.get('messages', [])]
    resp = infer_local_recommendations(msgs)
    print('FALLBACK RESULT:')
    print('reply:', resp.reply)
    print('recommendations:', [r.dict() for r in resp.recommendations])
    print('end_of_conversation:', resp.end_of_conversation)

def main():
    if len(sys.argv) < 2:
        print('Usage: test_post_trace.py path/to/converted.json')
        sys.exit(2)

    p = Path(sys.argv[1])
    if not p.exists():
        print('File not found:', p)
        sys.exit(2)

    payload = json.loads(p.read_text(encoding='utf-8'))

    url = 'http://localhost:8000/chat'
    try:
        r = requests.post(url, json=payload, timeout=5)
        print('HTTP', r.status_code)
        try:
            print(json.dumps(r.json(), indent=2, ensure_ascii=False))
        except Exception:
            print('Non-JSON response')
    except requests.exceptions.ConnectionError:
        print('Could not reach HTTP endpoint, running local fallback...')
        fallback_run(payload)

if __name__ == '__main__':
    main()
