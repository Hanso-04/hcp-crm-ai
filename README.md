# AI-First HCP CRM — Log Interaction Screen

An AI-first "Log HCP Interaction" module for pharma field reps, built for the
Round 1 technical assignment. A field rep never types into the structured
form directly — every field is filled or corrected by a **LangGraph agent**
running on Groq, driven from a conversational chat panel.

```
┌─────────────────────────────┐   ┌───────────────────────────┐
│  Log Interaction Form       │   │  AI Assistant (chat)      │
│  (React + Redux, read-only  │◄──┤  every message runs the   │
│  — populated only by the    │   │  LangGraph agent, which   │
│  agent's tool calls)        │   │  calls tools that patch   │
│                              │   │  the shared draft state   │
└─────────────────────────────┘   └───────────────────────────┘
              ▲                                 │
              │        FastAPI  /agent/chat     │
              └─────────────────────────────────┘
```

## Why it's built this way

The brief's reference video shows the form as read-only, with the AI
assistant as the sole way to populate or correct it. That single rule drove
every architectural decision here:

- **The frontend never computes or edits form values.** `LogInteractionForm`
  renders `state.interaction.draft` and nothing else — inputs are `readOnly`/
  `disabled`. The only writer of that Redux state is `applyAgentUpdate`,
  which fires exclusively from the `/agent/chat` response.
- **Edits are targeted patches, not re-logs.** `edit_interaction` asks the
  LLM to return *only* the field(s) that need to change, and the reducer
  merges that patch into the existing draft — every other field is left
  untouched. `log_interaction` (first-time logging) and `edit_interaction`
  (correcting a mistake) are deliberately separate tools for this reason.
- **A human still confirms before anything is saved.** The agent proposes
  and patches an in-memory draft; nothing hits the database until the rep
  clicks **Confirm & Save**, which calls `POST /interactions`. This keeps a
  human in the loop for a compliance-sensitive CRM record, while still
  satisfying "the AI, not the human, controls the form."

## The 5 LangGraph tools

| # | Tool | Required by brief? | What it does |
|---|------|---------------------|---------------|
| 1 | `log_interaction` | Yes | Parses the rep's free text (or a voice-note summary) into the structured fields (HCP name, type, date/time, attendees, topics, materials) and fills the form for the first time. |
| 2 | `edit_interaction` | Yes | Applies a **targeted correction** to one or more already-logged fields ("actually it was Dr. Mehta, not Dr. Shah") without touching anything else. |
| 3 | `fetch_hcp_history` | Our choice | Looks up the named HCP's last 5 logged interactions before a new one is filed, so the agent has context (and the rep doesn't have to repeat it). |
| 4 | `compliance_sentiment_flag` | Our choice | Reads the interaction text for HCP sentiment and pharma-compliance risk (off-label claims, adverse events, improper incentives) and flags the record for review. |
| 5 | `summarize_voice_note` | Our choice | Consent-gated — mirrors the "Summarize from Voice Note (Requires Consent)" control in the reference UI. Refuses to process a transcript unless the rep has ticked the consent box. |

Tools 3–5 were chosen specifically to read like a life-sciences product
decision rather than a generic CRUD tool list: history lookup makes the
agent context-aware across visits, the compliance tool answers to a real
pharma regulatory need, and the voice-note tool implements a control that
was actually shown in the reference video mock (the consent link visible in
the form screenshot), not just described in the text brief.

## Tech stack

- **Frontend:** React + Redux Toolkit, Inter font, plain CSS (no framework
  overhead needed for a two-pane layout).
- **Backend:** FastAPI, SQLAlchemy (Postgres or MySQL — swap via
  `DATABASE_URL`).
- **Agent:** LangGraph `StateGraph` — an `agent` node (Groq LLM bound to the
  5 tools) and a `tools` node (`ToolNode`), looping until the model responds
  without further tool calls.
- **LLM:** Groq `gemma2-9b-it` (mandated), with `llama-3.3-70b-versatile`
  wired in as a swappable fallback in `app/agent/llm.py` for turns needing
  heavier reasoning (e.g. long voice-note transcripts).

## Project structure

```
backend/
  app/
    agent/
      llm.py       # Groq client (primary + fallback model)
      state.py     # LangGraph shared state schema
      tools.py     # the 5 tools
      graph.py     # StateGraph wiring (agent <-> tools loop)
    routers/
      agent_router.py   # POST /agent/chat
      interactions.py   # POST/GET /interactions (the only DB writes)
    models.py      # SQLAlchemy Interaction table
    schemas.py      # Pydantic request/response models
    main.py         # FastAPI app + CORS
frontend/
  src/
    store/          # Redux: interactionSlice (the draft), chatSlice (messages)
    components/      # LogInteractionForm (locked form), ChatPanel
    api/agentApi.js   # calls to the FastAPI backend
```

## Running it locally

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # then fill in GROQ_API_KEY and DATABASE_URL
uvicorn app.main:app --reload --port 8000
```

Create your Groq key at https://console.groq.com/keys — the brief assumes
you generate a fresh one for this assignment. Point `DATABASE_URL` at a
running Postgres or MySQL instance (or use `sqlite:///./dev.db` for a
zero-setup local run — SQLAlchemy handles both).

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # REACT_APP_API_URL, defaults to localhost:8000
npm start
```

Opens on `http://localhost:3000`. Type a description into the chat panel
("Met Dr. Mehta, discussed Prodo-X efficacy, positive sentiment, shared
brochure") and watch the left-hand form fill itself.

## Testing the tool-calling loop without a Groq key

`app/agent/tools.py` and `app/agent/graph.py` are structured so each tool's
logic (and the full agent↔tools loop) can be unit-tested by mocking
`get_llm` — useful for verifying the "targeted patch" behavior of
`edit_interaction` or the consent gate on `summarize_voice_note` without
burning API calls.

## What I understood the assignment to be testing

Beyond the code itself, this brief is testing whether we can act like a
life-sciences product designer, not just wire up an LLM: does the tool list
reflect an actual pharma-sales workflow (history, compliance, consent) or a
generic CRUD demo; is the "AI writes, human confirms" interaction model
implemented as a real constraint (locked inputs + Redux write path) rather
than just described in a README; and is the LangGraph agent architected as
a genuine multi-step loop (recall history → log/edit → compliance check)
rather than a single prompt-and-respond call dressed up as five tools.
