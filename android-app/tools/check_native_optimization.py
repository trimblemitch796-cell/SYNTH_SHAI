"""Verify actual compile commands, not just requested CMake settings."""
import json
import shlex
from pathlib import Path
root = Path(__file__).resolve().parents[1] / 'app/.cxx'
files = list(root.rglob('compile_commands.json'))
assert files, 'No exported native compile commands'
checked = 0
for path in files:
    commands = json.loads(path.read_text())
    for entry in commands:
        source = entry['file']
        if not any(part in source for part in ('/ggml/', '/llama', '/chat.cpp')):
            continue
        args = entry.get('arguments') or shlex.split(entry['command'])
        opts = [a for a in args if a.startswith('-O')]
        assert opts and opts[-1] in ('-O2', '-O3'), (source, opts, args)
        checked += 1
assert checked, 'No inference sources checked'
print(f'PASS: {checked} native compile commands end with -O2/-O3')
