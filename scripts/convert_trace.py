#!/usr/bin/env python3
"""
Simple converter: turn a human-readable conversation trace into the JSON payload
expected by the FastAPI `/chat` endpoint.

Usage:
  python scripts/convert_trace.py path/to/trace.txt -o out.json

The parser is forgiving: it looks for lines containing "user" or "agent" (case-insensitive)
as role markers and collects following lines as that role's content until the next role marker.
If the trace already looks like JSON with a top-level `messages` array, it will be passed through.
"""
import argparse
from trace_converter import convert_text_to_messages
import json


def main():
    p = argparse.ArgumentParser()
    p.add_argument('trace', help='Path to trace file to convert')
    p.add_argument('-o', '--out', help='Output JSON file (defaults to stdout)')
    args = p.parse_args()

    txt = open(args.trace, 'r', encoding='utf-8').read()
    msgs = convert_text_to_messages(txt)
    out = {"messages": msgs}

    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f'Wrote {len(out.get("messages", []))} messages to {args.out}')
    else:
        print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
