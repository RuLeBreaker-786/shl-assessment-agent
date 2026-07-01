#!/usr/bin/env python3
"""
Batch convert all markdown traces in a folder to JSON payloads for /chat.
Also optionally POST each converted payload to the local /chat endpoint using the
existing test runner.

Usage:
  python scripts/batch_convert_traces.py traces/ -o traces/converted/ --post
"""
import argparse
from pathlib import Path
import json
from trace_converter import convert_file_to_json
import subprocess

def main():
    p = argparse.ArgumentParser()
    p.add_argument('indir', help='Directory with trace files')
    p.add_argument('-o', '--outdir', help='Output directory for converted JSON', default='traces/converted')
    p.add_argument('--post', action='store_true', help='POST each converted JSON to local /chat')
    args = p.parse_args()

    indir = Path(args.indir)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    for pth in sorted(indir.iterdir()):
        if pth.is_file() and pth.suffix.lower() in ('.txt', '.md'):
            out = convert_file_to_json(pth)
            outpath = outdir / (pth.stem + '.json')
            outpath.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
            print('Wrote', outpath)
            if args.post:
                # reuse test_post_trace script to POST
                subprocess.run(['python3', 'scripts/test_post_trace.py', str(outpath)])

if __name__ == '__main__':
    main()
