#!/usr/bin/env python3
"""
VuepressHope adapter post-processing step.
Called by UMDA after doc_output is populated.
Generates navbar.ts, sidebar.ts, theme.ts, config.ts from nav.yaml.
"""
from pathlib import Path
import runpy

# Just run adapter.py from same directory
adapter_path = Path(__file__).parent / "adapter.py"
runpy.run_path(str(adapter_path), run_name="__main__")
