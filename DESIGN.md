# Design & Evaluation Note

This document addresses the core design decisions, orchestration tradeoffs, and architectural modeling used to evaluate the Order Supervisor platform.

## 1. Architecture and Clarity of Design
The primary architectural goal was to build a system capable of handling long-running, multi-day tasks (e-commerce fulfillment) without locking up server threads or paying for idle LLM time. 

The architecture separates concerns into three distinct layers:
1. **Stateless API (FastAPI)**: Handles incoming webhooks and frontend requests instantly.
2. **Asynchronous Background Workers**: Offloads LLM reasoning to avoid blocking the main API thread.
3. **Database (PostgreSQL)**: Acts as the single source of truth, persisting the `activity_log` and `current_state` so the agents can safely shut down between events.

## 2. Quality of Tradeoff Reasoning
**Tradeoff: Single Constant Agent vs. Event-Driven Wakeups**
*   *Alternative:* Running a `while(True)` loop that constantly queries an LLM or `time.sleep()`.
*   *Why we rejected it:* Keeping an agent thread alive for a 5-day shipping period is horribly expensive, memory-intensive, and brittle against server restarts.
*   *Our Solution:* We treat the agent like a serverless function. It loads its context from the database, takes an action, and gracefully terminates itself using `set_sleep`. This allows the platform to scale to thousands of simultaneous orders on microscopic compute resources.

## 3. Orchestration Choices and Justification (The Dual-Agent Model)
We implemented a **Dual-Agent Orchestration** strategy natively, rejecting heavy frameworks like Langchain to maintain deterministic speed and strict control.
*   **The Classifier Agent:** A fast, cheap prompt designed exclusively to triage events ("Is this event urgent enough to wake the main agent?").
*   **The Main Reasoning Agent:** The heavy, tool-aware agent that executes business logic.
*   *Justification:* If an order receives 30 minor, non-actionable webhooks (e.g., "package scanned at warehouse"), we process them with the micro-cent Classifier rather than wasting the contextual tokens of the Main Agent.

## 4. State or Memory Design
Managing state over a multi-day workflow is the hardest challenge in agentic architecture. 
Our memory design relies on an **Append-Only Activity Log** combined with a **Mutable State Object**:
1.  **Activity Log:** An immutable ledger of every event, action, and reasoning block. When the agent wakes up, we feed it the tail of this log so it regains immediate short-term context.
2.  **State Object (`update_state` tool):** Over 5 days, the activity log grows too large for the LLM context window. We built an `update_state` tool that allows the agent to essentially "write sticky notes to itself" in a permanent JSON blob on the database, allowing it to remember critical tracking IDs perfectly for weeks without context-window overflow.

## 5. Event Handling
Events are processed asynchronously. When an event hits the backend (`/api/runs/{id}/events`), the API immediately returns `202 Accepted` to the caller. The event is pushed into the `activity_log`, and the Classifier is triggered dynamically in the background. This guarantees high-throughput webhook digestion without timeouts.

## 6. Frontend Usability
The Next.js frontend was designed to solve the "black box" problem of AI. It gives managers complete visibility into the AI's internal reasoning via the Activity Log UI. Furthermore, the human-in-the-loop override capabilities (Pause, Resume, and the "Add Instruction" box) ensure that human supervisors can dynamically steer the AI mid-workflow, hitting the perfect usability balance between automation and oversight.
