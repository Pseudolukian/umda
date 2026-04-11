#!/usr/bin/env python3
"""
Read a value from umda.yml by dot-path.
Usage: umda_conf.py <umda.yml> <dot.path>
Example: umda_conf.py umda.yml adapers.mkdocs.doc_output
"""
import sys, yaml

def resolve(data, path):
    for key in path.split('.'):
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return ''
    return str(data) if data is not None else ''

if len(sys.argv) < 3:
    print(f"Usage: {sys.argv[0]} <umda.yml> <dot.path>", file=sys.stderr)
    sys.exit(1)

with open(sys.argv[1], 'r', encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

print(resolve(cfg, sys.argv[2]))
