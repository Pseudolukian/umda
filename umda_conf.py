#!/usr/bin/env python3
"""
Read a value from umda.yml by dot-path.
Usage: umda_conf.py <umda.yml> <dot.path>
Example: umda_conf.py umda.yml adapers.mkdocs.doc_output
"""
import os
import re
import sys

import yaml

_ENV_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")

def resolve(data, path):
    for key in path.split('.'):
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return ''
    return data


def expand_env_vars(value):
    if not isinstance(value, str):
        return value

    def repl(match):
        name = match.group(1)
        default = match.group(2)
        env_val = os.getenv(name)
        if env_val is not None and env_val != "":
            return env_val
        if default is not None:
            return default
        raise ValueError(f"Environment variable '{name}' is not set")

    return _ENV_RE.sub(repl, value)

if len(sys.argv) < 3:
    print(f"Usage: {sys.argv[0]} <umda.yml> <dot.path>", file=sys.stderr)
    sys.exit(1)

with open(sys.argv[1], 'r', encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

try:
    value = resolve(cfg, sys.argv[2])
    value = expand_env_vars(value)
except ValueError as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(2)

print(str(value) if value is not None else '')
