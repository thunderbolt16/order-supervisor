# Order Supervisor Architecture

## 1. What is this project?
Imagine you run an e-commerce store and you need a dedicated employee watching every single order. If an order is delayed, they message logistics. If a refund is requested, they monitor it until it's paid. If there's an issue, they leave notes or contact the customer.

The **Order Supervisor** does exactly this, but using AI (Gemini). Instead of humans, AI agents are assigned to monitor orders. They "wake up" when events happen, decide if action is needed, use tools to take action, and then go back to "sleep" to save money and processing power.

---

## 2. High-Level Architecture

The project is split into two main parts: a **Python Backend** and a **React Frontend**.

### A. The Backend (Python + FastAPI)
This is the brain of the system. It receives events, talks to the AI, and saves everything to the database.

*   **FastAPI Engine**: We use FastAPI to create our API. It's very fast and handles incoming requests (like "new order created" or "payment failed").
*   **Background Processing**: We don't want the API to wait while the AI spends a minute thinking. So, when an event comes in, the backend immediately replies "Got it!" (HTTP 202 Accepted) and sends the actual AI work to a background task so the API remains fast.
*   **The Classifier (Fast AI)**: Waking up a powerful AI agent is expensive and slow. When an event happens while the main agent is "sleeping", we use a tiny, fast AI model (`CLASSIFIER_MODEL`, like Gemini 2.5 Flash). It looks at the event and quickly decides: "Should I wake up the main agent for this, or can it wait?"
*   **The Main Agent (Smart AI)**: If the classifier says "Wake up!", or if it's a scheduled wake-up, the main AI (`MAIN_AGENT_MODEL`, like Gemini 2.5 Flash) takes over. It reads the entire history of the order and decides what to do using tools.
*   **The Tools**: The AI can't click buttons, so we give it "tools" (code functions) it can call. For example: `message_logistics_team`, `update_state`, or `set_sleep`.
*   **The Scheduler (APScheduler)**: Orders take days to complete. The AI frequently says "I'll go to sleep, wake me up in 2 hours." The Scheduler is a background clock that ticks every minute, finds sleeping agents whose alarm has gone off, and wakes them up to check on the order.

### B. The Database (PostgreSQL)
We use PostgreSQL (with `asyncpg` and `SQLAlchemy`) to store everything asynchronously.

*   **Table: `supervisors`**: Defines *types* of agents. You can have an aggressive agent for VIP orders, and a relaxed agent for standard orders. This table stores the base instructions (the system prompt) for that type of agent.
*   **Table: `runs`**: A "run" represents one specific order being monitored. It tracks the current status (`running`, `sleeping`, `completed`) and stores a dynamic "current state" variable (like a JSON notepad the AI uses to remember things like tracking IDs).
*   **Table: `activity_log`**: The most important table. It acts as an immutable timeline. Every event, every time the AI thinks, every action it takes, and every time it sleeps is logged here. When the AI wakes up, we feed it this log so it remembers everything that happened historically.

### C. The Frontend (Next.js + Tailwind CSS)
This is the dashboard where human managers can watch the AI work.

*   **Framework**: Built with Next.js 14 using the App Router.
*   **Real-time Feel**: The dashboard frequently polls the backend API (every 3-5 seconds) to fetch the latest activity logs and run statuses, making it feel "live" as you watch the AI write notes and take actions.
*   **Control Panel**: Humans can step in. They can inject manual events, add new instructions (e.g., "Ignore the next delay for this order"), pause the AI, or manually terminate a run.

---

## 3. How the AI Loop Works

This is the exact sequence of events when an order is being monitored:

1.  **Event Arrives**: Imagine a "payment_failed" event is sent to the API.
2.  **Triage**: The fast Classifier AI looks at it. It says, "Yes, payment failed is important. Wake the agent!"
3.  **Wake Up**: The Main Agent is woken up. It's given its System Prompt (instructions) and the entire `activity_log` for this order.
4.  **Thinking & Acting**: The AI reads the history. It decides to use the tool `message_payments_team`. The backend executes this tool and logs the action.
5.  **Looping**: The AI is given the tool result and asked, "Anything else?" It might decide to use another tool, like `update_state` to note the payment issue.
6.  **Sleeping**: Eventually, the AI has nothing left to do right now. It uses the `set_sleep` tool, specifying a duration (e.g., "Sleep for 60 minutes"). The database status changes to `sleeping`, and the backend stops processing.
7.  **Auto-Completion**: The system continuously checks if the order is done. If a "delivered" event is logged, or a refund is fully processed, or if the run maxes out its allowed lifespan (e.g., 72 hours), the system automatically ends the run and asks the AI to create a Final Summary of everything it handled.

---

## 4. How to Run the Project

You need **Python 3.11+**, **Node.js 18+**, and an empty **PostgreSQL database** (we recommend a free Supabase database).

### Step 1: Environment Variables
Create a file named `.env` in the root folder with your backend settings. Use your database credentials and Gemini API key here:
```env
DATABASE_URL=postgresql+asyncpg://postgres.your_db_ref:your_password@aws-0-group.pooler.supabase.com:5432/postgres
GEMINI_API_KEY=sk-ant-your-api-key
```
*(Note: If using Supabase, make sure to use the "Session pooler" connection string, not the direct one).*

Create a file named `.env.local` inside the `frontend/` folder:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Step 2: Initialize the Database
Open a terminal in the root folder and run:
```bash
# Install backend dependencies
cd backend
pip install -r requirements.txt
cd ..

# Run the initialization script
python -m backend.db.init_db
```
This will quickly create all the tables (`supervisors`, `runs`, `activity_log`) and insert a default supervisor configuration.

### Step 3: Run the Backend
Keep your terminal in the root folder and start the FastAPI server:
```bash
uvicorn backend.main:app --reload --port 8000
```
The backend API is now running on `http://localhost:8000`. The background scheduler also starts automatically.

### Step 4: Run the Frontend
Open a **new terminal** window, go to the frontend folder, and start Next.js:
```bash
cd frontend
npm install
npm run dev
```
Visit `http://localhost:3000` in your web browser.

You will see the Order Supervisor dashboard. You can click "New Run", give it an order ID, and watch the AI supervisor in action!
