"""Syntax/template checks; does not import OpenViking or contact the user's Mac."""
import ast
import json
from pathlib import Path
import plistlib

ROOT = Path(__file__).resolve().parents[2]
for folder in ('ops/scripts', 'ops/tests'):
    for path in (ROOT/folder).glob('*.py'):
        ast.parse(path.read_text(), filename=str(path))
for path in [ROOT/'package.json', *(ROOT/'ops/config').glob('*.json')]:
    json.loads(path.read_text())
plistlib.loads((ROOT/'ops/config/ai.openviking.server.plist.template').read_bytes())
print('Python syntax, JSON templates and launchd plist passed')
