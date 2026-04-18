import sys

def rewrite():
    with open('backend/agent/runtime.py', 'r') as f:
        src = f.read()

    start_str = "    # ------------------------------------------------------------------ #\n    # 6–7. Agentic loop\n    # ------------------------------------------------------------------ #\n"
    start_idx = src.find(start_str)
    
    end_str = "        await db.commit()\n\n    # ------------------------------------------------------------------ #\n    # 9. Terminal-completion check"
    end_idx = src.find(end_str)
    
    if start_idx == -1 or end_idx == -1:
        print("COULD NOT FIND START OR END IDX")
        print("start:", start_idx, "end:", end_idx)
        return

    new_loop = """    # ------------------------------------------------------------------ #
    # 6–7. Agentic loop
    # ------------------------------------------------------------------ #
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    model = run_row.supervisor_model or settings.MAIN_AGENT_MODEL

    from backend.agent.tools import TOOLS
    gemini_tools = [{"function_declarations": TOOLS}]
    contents = [
        types.Content(role="user", parts=[types.Part.from_text(text=context_message)])
    ]

    for iteration in range(MAX_AGENT_ITERATIONS):
        logger.debug("run_id=%s  agent iteration=%d", run_id, iteration)

        # ── Gemini API call with error handling ───────────────────────
        try:
            response = await client.aio.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=gemini_tools,
                    max_output_tokens=2048,
                )
            )
        except Exception as api_exc:
            logger.error(
                "Gemini API error  run_id=%s  iter=%d: %s",
                run_id, iteration, api_exc,
            )
            await _log_entry(
                db, run_id, "agent_reasoning",
                {
                    "error": str(api_exc),
                    "fallback": "agent cycle failed, will retry on next scheduled wake",
                },
            )
            await _set_sleeping(db, run_id, _API_ERROR_SLEEP_MINUTES)
            await db.commit()
            return  # abandon this cycle; scheduler will retry

        candidate = response.candidates[0] if response.candidates else None
        if not candidate or not candidate.content:
            text_part = response.text if hasattr(response, 'text') else ""
            if text_part:
               await _log_entry(db, run_id, "agent_reasoning", {"text": text_part, "iteration": iteration})
            
            duration = run_row.default_wake_interval_minutes
            await _set_sleeping(db, run_id, duration)
            await _log_entry(db, run_id, "agent_sleep", {"reason": "no candidate generated", "duration_minutes": duration})
            await db.commit()
            break
            
        model_content = candidate.content
        contents.append(model_content)

        text_blocks = [p.text for p in model_content.parts if p.text]
        tool_blocks = [p.function_call for p in model_content.parts if p.function_call]

        # Log any inline text as reasoning
        if text_blocks:
            reasoning_text = "\\n".join(text_blocks)
            await _log_entry(
                db, run_id, "agent_reasoning",
                {"text": reasoning_text, "iteration": iteration},
            )

        # ---- 8. No tool calls → default sleep -------------------------
        if not tool_blocks:
            duration = run_row.default_wake_interval_minutes
            await _set_sleeping(db, run_id, duration)
            await _log_entry(
                db, run_id, "agent_sleep",
                {
                    "reason": "agent returned with no tool calls",
                    "duration_minutes": duration,
                    "iteration": iteration,
                },
            )
            await db.commit()
            break

        # ---- 7. Process each tool call --------------------------------
        tool_responses = []
        sleep_invoked = False

        for tool_call in tool_blocks:
            # Note: Gemini args is often empty if no params, or dict-like
            inp_args = {k: v for k, v in tool_call.args.items()} if getattr(tool_call, "args", None) else {}
            
            result_text, should_return = await _execute_tool(
                db, run_id, tool_call.name, inp_args, run_row
            )
            
            tool_responses.append(
                types.Part.from_function_response(
                    name=tool_call.name,
                    response={"result": result_text}
                )
            )
            
            if should_return:
                sleep_invoked = True
                break  # set_sleep stops further tool processing

        await db.commit()

        if sleep_invoked:
            return
            
        contents.append(types.Content(role="user", parts=tool_responses))
        
    else:
        # Safety: exceeded MAX_AGENT_ITERATIONS
        logger.warning("run_id=%s hit MAX_AGENT_ITERATIONS (%d)", run_id, MAX_AGENT_ITERATIONS)
        duration = run_row.default_wake_interval_minutes
        await _set_sleeping(db, run_id, duration)
        await _log_entry(
            db, run_id, "agent_sleep",
            {"reason": "max iterations reached", "duration_minutes": duration},
        )
"""
    src = src[:start_idx] + new_loop + src[end_idx:]
    with open("backend/agent/runtime.py", "w") as f:
        f.write(src)

if __name__ == "__main__":
    rewrite()
