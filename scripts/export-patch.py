#!/usr/bin/env python3
"""Export the committed source changes against the recorded upstream base."""
import json, subprocess
from pathlib import Path
root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / 'source.json').read_text())
source = root / manifest['checkout']
patch = subprocess.check_output([
    'git', '-C', str(source), 'diff', '--binary', '--no-ext-diff', '--no-color',
    manifest['base'], 'HEAD',
])
(root / 'patches').mkdir(exist_ok=True)
(root / 'patches' / 'firefox-harmony.patch').write_bytes(patch)
