# Financial Services Multi-Agent System

A hierarchical AI assistant for financial services built with LangGraph, featuring 6 specialized agents coordinated by a central supervisor. The system handles database queries, document retrieval, web research, data visualization, and general financial Q&A through a single conversational interface.

---

## Project Goal

Build a production-grade multi-agent system that can answer any financial question by routing it to the most appropriate specialized agent — whether the answer lives in a database, a regulatory document, the web, or general LLM knowledge.

---

## Architecture

```
User Query
    ↓
Main Supervisor (routes to correct agent)
    ↓
┌─────────────────────────────────────────────────────┐
│  SQL Agent          → PostgreSQL financial database  │
│  RAG Agent          → indexed financial documents    │
│  Conversation Agent → general LLM knowledge         │
│  Visualization Agent→ interactive Chart.js charts   │
│  Web Research Team  → live web search + reports     │
└─────────────────────────────────────────────────────┘
    ↓
Response returned to user
```

---

## Agents

### Main Supervisor
Routes every user query to the correct agent based on intent detection. Uses LLM-based classification to identify whether the query needs database data, document knowledge, live web search, a chart, or general explanation.

**Routing logic:**
- `sql` → questions about customers, accounts, transactions, loans, investments
- `rag` → questions about financial regulations, reports, or indexed documents
- `conversation` → general financial concepts, definitions, explanations
- `visualization` → any request mentioning chart, graph, plot, or visual
- `web_research` → current events, live prices, latest news, recent trends

---

### SQL Agent
Queries a PostgreSQL financial database using natural language. The LLM generates accurate SQL queries based on the user's question and returns results formatted in natural language with customer names resolved from IDs.

**Database schema:**
```
customers    (id, name, email, country, account_type)
accounts     (id, customer_id, balance, currency, status)
transactions (id, account_id, type, amount, date, status)
loans        (id, customer_id, amount, interest_rate, due_date, status)
investments  (id, customer_id, asset_name, amount_invested, current_value)
```

**Example queries:**
- "What is the total balance across all active accounts?"
- "How many customers have overdue loans?"
- "Show me all completed transactions"

---

### RAG Agent
Retrieves answers from indexed financial documents using FAISS vector store and HuggingFace embeddings (`all-MiniLM-L6-v2`). Uses `k=8` retrieval with a carefully tuned prompt to balance cross-document synthesis with hallucination prevention.

**Indexed documents:**
- JPMorgan Chase Annual Report 2023
- Federal Reserve Financial Stability Report (November 2024)
- Basel III Framework (BIS)
- IMF — The Macroeconomic Costs of Conflict (2020)
- IMF — Geopolitical Risks: Implications for Asset Prices (2025)

**Example queries:**
- "What is the minimum capital requirement under Basel III?"
- "What are the main vulnerabilities in the US financial system?"
- "What is the long term economic impact of civil war?"

---

### Conversation Agent
Handles general financial Q&A using the LLM's built-in knowledge. No tools, no retrieval — just the LLM with a financial system prompt and full conversation memory across turns.

**Example queries:**
- "What is compound interest?"
- "Explain the difference between stocks and bonds"
- "What does APR mean?"

---

### Visualization Agent
Generates interactive Chart.js charts from database data. Uses a two-step pipeline: LLM generates the SQL query from natural language, executes it, then LLM determines the chart type and column mapping dynamically from the actual results. Outputs self-contained HTML files that open in any browser.

**Supported chart types:** bar, line, pie, scatter, histogram

**Example queries:**
- "Show me a bar chart of account balances by customer"
- "Pie chart of loan status distribution"
- "Line chart of loan amounts by customer"

---

### Web Research Team (Subgraph)
A hierarchical subgraph of 3 agents that handles live web research:

**Researcher Agent** — runs 2 targeted web searches using SerpAPI (original query + financial analysis variant) and collects raw results.

**Report Writer Agent** — synthesizes raw research into a structured response. Automatically chooses the format based on query type:
- Simple fact → 1-2 sentence answer
- News/events → 3-5 bullet point summary
- Analysis/trends → full structured report (Executive Summary, Key Findings, Market Implications, Conclusion)

**Sub-Supervisor** — coordinates the researcher and report writer, manages the subgraph flow.

**Example queries:**
- "What is the current price of gold?"
- "What are the latest Fed interest rate news?"
- "What are the latest trends in AI investment in 2025?"

---

## Project Structure

```
multi-agent system/
├── config.py                      # shared LLM initialization (ChatGroq)
├── utils.py                       # shared database utility (run_sql_query)
├── supervisor.py                  # main graph, routing, compiled app
├── .env                           # API keys
├── database/
│   └── create_db.py               # PostgreSQL setup and seed data
|   ├── faiss_index/               # saved FAISS vector store
├── agents/
│   ├── sql_agent.py               # SQL tool + agent node
│   ├── rag_agent.py               # FAISS loader + RAG chain + agent node
│   ├── conversation_agent.py      # LLM agent node with memory
│   ├── visualization_agent.py     # Chart.js HTML generator + agent node
│   └── web_research/
│       ├── __init__.py
│       ├── researcher.py          # SerpAPI search node
│       ├── report_writer.py       # report synthesis node
│       └── sub_supervisor.py      # web research subgraph
├── rag-docs/                      # financial PDFs for RAG indexing│   
└── charts/                        # generated Chart.js HTML files
```

---

## Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 16

### Installation

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install langchain langchain-groq langchain-community langgraph \
            langsmith python-dotenv psycopg2-binary pymupdf \
            langchain-huggingface faiss-cpu sentence-transformers \
            torch google-search-results
```

### Environment Variables

Create a `.env` file in the root:

```
GROQ_API_KEY=your-groq-api-key
LANGSMITH_API_KEY=your-langsmith-api-key
LANGSMITH_TRACING=true
LANGCHAIN_PROJECT=financial-multi-agent
SERPAPI_API_KEY=your-serpapi-api-key
```

### Database Setup

```bash
# create PostgreSQL database
psql postgres
CREATE DATABASE financial_db;
CREATE USER financial_user WITH PASSWORD 'yourpassword';
GRANT ALL PRIVILEGES ON DATABASE financial_db TO financial_user;
\q

# populate with sample data
cd database
python3 create_db.py
```

### Build FAISS Index

Download the 5 financial PDFs into `rag-docs/` and run the exploration notebook to build and save the FAISS index to `database/faiss_index/`.

### Run

```bash
python3 supervisor.py
```

---

## Tech Stack

| Category | Tool |
|----------|------|
| LLM Provider | Groq (llama-3.3-70b-versatile) |
| Agent Framework | LangGraph |
| Database | PostgreSQL 16 |
| Vector Store | FAISS |
| Embeddings | HuggingFace all-MiniLM-L6-v2 |
| Web Search | SerpAPI |
| Visualization | Chart.js |
| Monitoring | LangSmith |
| Language | Python 3.11 |

---

## LangSmith Tracing

All agent runs are automatically traced in LangSmith under the `financial-multi-agent` project. Each run shows the full execution path including which agent was selected, tool calls made, tokens used, and response latency.

---

## Current Status

| Component | Status |
|-----------|--------|
| SQL Agent | ✅ Complete |
| RAG Agent | ✅ Complete |
| Conversation Agent | ✅ Complete |
| Visualization Agent | ✅ Complete |
| Web Research Team | ✅ Complete |
| Main Supervisor | ✅ Complete |
| ChainLit UI | ⏳ In Progress |

---

## Known Limitations

- Visualization agent currently generates HTML files — ChainLit will display them inline
- Web search response time is 10-15 seconds due to 2 sequential SerpAPI calls
- RAG answers limited to the 5 indexed documents — expanding the document set improves coverage
- Database contains sample data — production deployment would connect to a live financial database
