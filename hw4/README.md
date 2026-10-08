# Campus Customs

A Yale apparel shop with a PydanticAI shop assistant, built for MGT 409 (Yale School of Management).

A React + Vite + TypeScript front end, a FastAPI back end, and an agent that answers from the shop's own SQLite catalogue — real prices, real colours, real stock by size.

---

## Before you start: the data pack

The course data pack is **not in this repository** (it is git-ignored). Put it at `hw4/data/` so the layout is:

```
hw4/
└── data/
    ├── campus_customs.db     # the shop database
    └── products/             # the product photographs
```

Nothing will run without it — the API refuses to start a request if the database is missing.

## Setup

From inside `hw4/`:

```bash
# 1. Python environment
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Front-end packages
cd frontend && npm install && cd ..

# 3. Tables added in Problem 9 (discounts, purchases, ratings).
#    Safe to re-run; it never touches the seeded tables.
cd backend && ../.venv/bin/python schema.py && cd ..

# 4. Lift the product photos off their backgrounds so garments float on the
#    page. Writes data/products_cutout/. Takes about a minute for 102 images.
#    Optional — the site falls back to the original photos without it.
cd backend && ../.venv/bin/python cutouts.py && cd ..
```

### The API key

`PORTKEY_API_KEY` is read from a `.env` file in the directory **above** `hw4/`. Copy `.env.example`, rename it to `.env`, put it one level up, and fill in your key. The real `.env` is git-ignored and is never committed.

## Running it

Two processes, in two terminals.

**Terminal 1 — the back end.** It must be run **from `backend/`**, because `main.py` imports its neighbours as plain modules:

```bash
cd backend
../.venv/bin/python -m uvicorn main:app --reload --reload-include "*.md" --port 8000
```

> `--reload-include "*.md"` is worth keeping. Uvicorn's reloader watches `*.py` only by default, so editing `prompts/prompt.md` will not restart the server and the agent will keep serving its cached prompt.

**Terminal 2 — the front end:**

```bash
cd frontend
npm run dev
```

Then open **http://localhost:5174**. Vite proxies `/api` and `/media` through to port 8000, so the browser stays on one origin.

### Signing in

The seeded database includes a test account:

```
test@campuscustoms.yale.edu  /  password
```

Signing in turns on the member features: Handsome Dan's occasional 10% discount, a conversation that is remembered between visits, and buying with a star rating.

## What is here

```
hw4/
├── AI_prompts.md          every prompt typed to the vibe coder, per problem
├── requirements.txt
├── .env.example
├── README.md
├── frontend/              Vite + React + TypeScript
├── backend/
│   ├── main.py            FastAPI app — the one to run with uvicorn
│   ├── agent.py           the agent: prompt + model + tools
│   ├── tools.py           the tools the agent can call
│   ├── models.py          Pydantic types
│   ├── prompts/prompt.md  the system prompt
│   ├── auth.py            accounts and password hashing
│   ├── db.py              read-only catalogue access
│   ├── history.py         chat history for signed-in shoppers
│   ├── perks.py           discounts, purchases and ratings
│   ├── mascot.py          Handsome Dan's discount line
│   ├── audit.py           the append-only audit trail
│   ├── schema.py          migration for the Problem 9 tables
│   └── cutouts.py         background removal for product photos
└── output/
    ├── harness.md         how the whole system works
    ├── design.md          the styling pass
    ├── usability.md       the Problem 9 improvements
    ├── app_check.html     live-site test report (open it in a browser)
    ├── app_check_images/  screenshots linked from app_check.html
    ├── screenshots/       supporting screenshots referenced by harness.md
    └── audit_trail.json   append-only record of agent runs
```

**The agent itself is four files**: `backend/prompts/prompt.md`, `backend/agent.py`, `backend/tools.py`, and `backend/models.py`. The rest of `backend/` is the shop around it.

Start with **[output/harness.md](output/harness.md)** for how the system fits together, or open **[output/app_check.html](output/app_check.html)** in a browser to see it working.

## Notes

- The catalogue database is opened **read-only** by everything except account registration, chat history, and the purchase/rating tables.
- Passwords are stored as PBKDF2-SHA256 with 120,000 iterations and a per-user salt. The plain password is never stored or logged.
- The assistant has no tool that can read the `users` table, so it cannot reach anybody's account.
- Sessions live in the API process's memory, so restarting the back end signs everyone out.

---

A course project. Not affiliated with Yale University.
