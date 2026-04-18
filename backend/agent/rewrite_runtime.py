import sys

def rewrite():
    with open('backend/agent/runtime.py', 'r') as f:
        src = f.read()

    # 1. Imports
    src = src.replace('import anthropic', 'from google import genai\nfrom google.genai import types')
    
    # 2. _execute_tool signature
    old_tool_sig = """async def _execute_tool(
    db: AsyncSession,
    run_id: str,
    tool_use: Any,
    supervisor: Any,
) -> tuple[str, bool]:
    \"\"\"Execute a single tool call.

    Returns:
        (result_content, should_return) — should_return=True means the caller
        must stop the agent loop immediately (set_sleep was invoked).
    \"\"\"
    name: str = tool_use.name
    inp: dict = tool_use.input"""
    
    new_tool_sig = """async def _execute_tool(
    db: AsyncSession,
    run_id: str,
    name: str,
    inp: dict,
    supervisor: Any,
) -> tuple[str, bool]:
    \"\"\"Execute a single tool call."""
    src = src.replace(old_tool_sig, new_tool_sig)

    # 3. complete_run
    old_complete = """        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        summary_prompt = (
            "You are reviewing a completed order supervision run. "
            "Based on the activity log below, produce a JSON summary.\\n\\n"
            "Return ONLY valid JSON matching this schema exactly:\\n"
            '{"summary": "string", "actions_taken": ["..."], '
            '"key_learnings": ["..."], "recommendations": ["..."]}\\n\\n'
            f"Activity log:\\n{activity_text}"
        )

        try:
            response = await client.messages.create(
                model=settings.MAIN_AGENT_MODEL,
                max_tokens=1024,
                messages=[{"role": "user", "content": summary_prompt}],
            )
            raw = response.content[0].text.strip()"""
            
    new_complete = """        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        summary_prompt = (
            "You are reviewing a completed order supervision run. "
            "Based on the activity log below, produce a JSON summary.\\n\\n"
            "Return ONLY valid JSON matching this schema exactly:\\n"
            '{"summary": "string", "actions_taken": ["..."], '
            '"key_learnings": ["..."], "recommendations": ["..."]}\\n\\n'
            f"Activity log:\\n{activity_text}"
        )

        try:
            response = await client.aio.models.generate_content(
                model=settings.MAIN_AGENT_MODEL,
                contents=summary_prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=1024,
                    response_mime_type="application/json"
                )
            )
            raw = response.text.strip()"""
    src = src.replace(old_complete, new_complete)
    
    # 3.1 fix catch block for complete_run APIError if any
    src = src.replace('except anthropic.APIError', 'except Exception')
    
    with open('backend/agent/runtime.py', 'w') as f:
        f.write(src)

rewrite()
