#!/usr/bin/env python3
"""
Resolve the live BASE_URL for a given Railway environment by querying Railway CLI JSON.

Usage:
  python scripts/resolve_base_url.py --env develop

Requirements:
  - Railway CLI installed and logged in, or RAILWAY_TOKEN set in env
  - Project should be linked in this workspace (railway link)

Output:
  Prints a single https URL, e.g. https://yoto-smart-stream-develop.up.railway.app
"""
import argparse
import json
import os
import re
import subprocess
import sys
from typing import Any, Iterable


def run(cmd: list[str]) -> str:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return out.decode().strip()
    except subprocess.CalledProcessError as e:
        sys.stderr.write(e.output.decode(errors='ignore'))
        raise


def flatten_strings(obj: Any) -> Iterable[str]:
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from flatten_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from flatten_strings(v)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--env', default='develop', help='Railway environment name (develop|production|staging)')
    args = parser.parse_args()

    # Fetch status JSON from Railway CLI
    data_raw = run(['railway', 'status', '--json'])
    try:
        data = json.loads(data_raw)
    except json.JSONDecodeError:
        sys.stderr.write('Failed to parse Railway status JSON.\n')
        return 2

    # Collect candidate domains from JSON
    candidates = list(set(flatten_strings(data)))
    # Domain patterns to consider
    pat = re.compile(r'^(https?://)?([a-zA-Z0-9\-]+)\.up\.railway\.app/?$')

    # Prefer domains that include the env name
    env = args.env.lower()
    scored: list[tuple[int, str]] = []
    for s in candidates:
        m = pat.match(s)
        if not m:
            continue
        domain = s if s.startswith('http') else f'https://{s}'.rstrip('/')
        score = 0
        if env in domain:
            score += 2
        # slight preference for our project name if present
        if 'yoto-smart-stream' in domain:
            score += 1
        scored.append((score, domain.rstrip('/')))

    if not scored:
        sys.stderr.write('No Railway domains found in status JSON.\n')
        return 3

    # Pick best-scoring candidate
    scored.sort(reverse=True)
    best = scored[0][1]
    print(best)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
