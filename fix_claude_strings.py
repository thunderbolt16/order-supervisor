import os

files_to_fix = [
    'README.md',
    'ARCHITECTURE.md',
    'backend/models.py',
    'backend/db/schema.sql',
    'backend/db/seed.sql',
    'frontend/app/supervisors/page.tsx',
    'backend/agent/tools.py',
    'backend/agent/runtime.py'
]

replacements = {
    'Anthropic API key': 'Gemini API key',
    'ANTHROPIC_API_KEY': 'GEMINI_API_KEY',
    'claude-haiku-4-5-20251001': 'gemini-2.5-flash',
    'claude-sonnet-4-6': 'gemini-2.5-flash',
    'claude-3-haiku-20240307': 'gemini-2.5-flash',
    'claude-3-5-sonnet-20241022': 'gemini-2.5-flash',
    '(Claude)': '(Gemini)',
    '(like Claude Haiku)': '(like Gemini 2.5 Flash)',
    '(like Claude Sonnet)': '(like Gemini 2.5 Flash)',
    'persistent Claude agent': 'persistent Gemini agent',
    'Calls Claude': 'Calls Gemini',
    'calls Claude': 'calls Gemini',
    'Claude signaled': 'Gemini signaled',
    'Claude tool': 'Gemini tool',
    'claude model': 'gemini model',
}

for file_path in files_to_fix:
    if not os.path.exists(file_path):
        continue
    with open(file_path, 'r') as f:
        content = f.read()
        
    for old, new in replacements.items():
        content = content.replace(old, new)
        
    with open(file_path, 'w') as f:
        f.write(content)

