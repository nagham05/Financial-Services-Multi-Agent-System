import os
from dotenv import load_dotenv
load_dotenv()

import uuid
from langchain_core.messages import HumanMessage
from supervisor import app

# test cases: (query, expected_agent, expected_keywords_in_response)
TEST_CASES = [
    # ── SQL Agent ──────────────────────────────────────────────────────────────
    ("What is the total balance across all active accounts?", "sql", ["57,000", "57000"]),
    ("How many customers have overdue loans?", "sql", ["2"]),
    ("Which customer has the highest account balance?", "sql", ["bob johnson", "15,000"]),
    ("Show me all frozen accounts", "sql", ["frozen", "charlie brown", "fiona"]),
    ("What is the average loan interest rate?", "sql", ["interest", "%"]),
    # new SQL cases
    ("List all customers from the USA", "sql", ["usa", "united states", "customer"]),
    ("How many transactions are pending?", "sql", ["pending", "transaction"]),
    ("What is the total amount of all active loans?", "sql", ["loan", "total", "$"]),
    ("Which customer has the most investments?", "sql", ["investment", "customer"]),
    ("Show all completed transactions above $1000", "sql", ["completed", "transaction", "1,000"]),
    ("What is the total current value of all investments?", "sql", ["investment", "value", "$"]),
    ("How many accounts are active vs frozen?", "sql", ["active", "frozen"]),
    ("Which loans are overdue and what are their amounts?", "sql", ["overdue", "loan", "$"]),

    # ── RAG Agent ─────────────────────────────────────────────────────────────
    ("What is the minimum capital requirement under Basel III?", "rag", ["6%", "8%", "basel"]),
    ("What are the main vulnerabilities in the US financial system?", "rag", ["valuation", "leverage", "funding"]),
    ("How does war affect GDP per capita?", "rag", ["gdp", "conflict", "percent"]),
    ("What is the countercyclical capital buffer?", "rag", ["buffer", "2.5", "credit"]),
    ("What were JPMorgan's key risks in 2023?", "rag", ["jpmorgan", "risk", "cyber"]),
    # new RAG cases
    ("What is Tier 1 capital under Basel III?", "rag", ["tier 1", "capital", "6%"]),
    ("What geopolitical risks does the IMF highlight in 2025?", "rag", ["geopolitical", "risk", "imf"]),
    ("How does armed conflict affect private consumption?", "rag", ["consumption", "conflict", "percent"]),
    ("What does the Federal Reserve say about equity market valuations?", "rag", ["equity", "valuation", "federal reserve"]),
    ("What are JPMorgan's operational risks?", "rag", ["operational", "risk", "jpmorgan"]),
    ("What is the capital conservation buffer?", "rag", ["conservation", "buffer", "2.5"]),
    ("How does conflict affect manufacturing output?", "rag", ["manufacturing", "conflict", "percent"]),

    # ── Conversation Agent ────────────────────────────────────────────────────
    ("What is compound interest?", "conversation", ["interest", "principal", "growth"]),
    ("What is a hedge fund?", "conversation", ["hedge", "fund", "investment"]),
    ("Explain the difference between APR and APY", "conversation", ["apr", "apy", "rate"]),
    ("What is a bear market?", "conversation", ["bear", "market", "decline"]),
    ("How does inflation affect purchasing power?", "conversation", ["inflation", "purchasing", "price"]),
    # new conversation cases
    ("What is diversification in investing?", "conversation", ["diversif", "risk", "portfolio"]),
    ("What is the difference between stocks and bonds?", "conversation", ["stock", "bond", "equity"]),
    ("What is a mutual fund?", "conversation", ["mutual fund", "portfolio", "investor"]),
    ("What does liquidity mean in finance?", "conversation", ["liquid", "cash", "asset"]),
    ("What is dollar cost averaging?", "conversation", ["dollar cost", "invest", "average"]),
    ("How does the central bank control inflation?", "conversation", ["central bank", "interest rate", "inflation"]),

    # ── Visualization Agent ───────────────────────────────────────────────────
    ("Show me a pie chart of loan status distribution", "visualization", ["chart", "charts/"]),
    ("Bar chart of account balances by customer", "visualization", ["chart", "charts/"]),
    ("Show me a line chart of loan amounts by customer", "visualization", ["chart", "charts/"]),
    # new visualization cases
    ("Create a bar chart showing total investments per customer", "visualization", ["chart", "charts/"]),
    ("Plot a pie chart of account types", "visualization", ["chart", "charts/"]),
    ("Visualize the distribution of transaction statuses", "visualization", ["chart", "charts/"]),
    ("Generate a chart of loan interest rates by customer", "visualization", ["chart", "charts/"]),

    # ── Web Research Team ─────────────────────────────────────────────────────
    ("What is the current price of gold?", "web_research", ["gold", "$", "ounce"]),
    ("What are the latest Fed interest rate news?", "web_research", ["federal reserve", "rate", "%"]),
    ("How are global markets performing today?", "web_research", ["market", "index", "performance"]),
    # new web research cases
    ("What is the current Bitcoin price?", "web_research", ["bitcoin", "$", "btc"]),
    ("What are the latest US inflation figures?", "web_research", ["inflation", "cpi", "%"]),
    ("What is the current S&P 500 level?", "web_research", ["s&p", "500", "index"]),
    ("What are the latest earnings results for Apple?", "web_research", ["apple", "earnings", "revenue"]),
    ("What is the current EUR/USD exchange rate?", "web_research", ["eur", "usd", "exchange"]),
]


def evaluate():
    results = []
    total = len(TEST_CASES)

    routing_correct = 0
    response_correct = 0

    print(f"\n{'='*60}")
    print(f"Running {total} test cases...")
    print(f"{'='*60}\n")

    for i, (query, expected_agent, expected_keywords) in enumerate(TEST_CASES):
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}

        try:
            result = app.invoke(
                {"messages": [HumanMessage(content=query)]},
                config=config
            )

            actual_agent = result.get("next_agent", "unknown")
            response = result["messages"][-1].content.lower()

            # check routing accuracy
            routing_ok = actual_agent == expected_agent
            if routing_ok:
                routing_correct += 1

            # check response accuracy (at least one keyword must be present)
            response_ok = any(kw.lower() in response for kw in expected_keywords)
            if response_ok:
                response_correct += 1

            status = "✅" if (routing_ok and response_ok) else "❌"
            routing_status = "✅" if routing_ok else f"❌ (got {actual_agent})"
            response_status = "✅" if response_ok else "❌"

            print(f"Test {i+1}/{total}: {status}")
            print(f"  Query:    {query[:70]}")
            print(f"  Routing:  {routing_status}")
            print(f"  Response: {response_status}")
            print()

            results.append({
                "query": query,
                "expected_agent": expected_agent,
                "actual_agent": actual_agent,
                "routing_ok": routing_ok,
                "response_ok": response_ok
            })

        except Exception as e:
            print(f"Test {i+1}/{total}: ❌ ERROR")
            print(f"  Query: {query[:70]}")
            print(f"  Error: {str(e)}\n")
            results.append({
                "query": query,
                "expected_agent": expected_agent,
                "actual_agent": "error",
                "routing_ok": False,
                "response_ok": False
            })

    # ── Summary ───────────────────────────────────────────────────────────────
    routing_accuracy = (routing_correct / total) * 100
    response_accuracy = (response_correct / total) * 100
    overall_accuracy = ((routing_correct + response_correct) / (total * 2)) * 100

    print(f"{'='*60}")
    print(f"EVALUATION RESULTS")
    print(f"{'='*60}")
    print(f"Total test cases:     {total}")
    print(f"Routing accuracy:     {routing_correct}/{total} ({routing_accuracy:.1f}%)")
    print(f"Response accuracy:    {response_correct}/{total} ({response_accuracy:.1f}%)")
    print(f"Overall accuracy:     {overall_accuracy:.1f}%")
    print(f"{'='*60}")

    # ── Per-agent breakdown ───────────────────────────────────────────────────
    agents = ["sql", "rag", "conversation", "visualization", "web_research"]
    print(f"\nPER-AGENT ROUTING BREAKDOWN:")
    for agent in agents:
        agent_cases = [r for r in results if r["expected_agent"] == agent]
        agent_correct = sum(1 for r in agent_cases if r["routing_ok"])
        print(f"  {agent:<15} {agent_correct}/{len(agent_cases)}")

    # ── Failed cases ──────────────────────────────────────────────────────────
    failed = [r for r in results if not r["routing_ok"] or not r["response_ok"]]
    if failed:
        print(f"\nFAILED CASES ({len(failed)}):")
        for r in failed:
            print(f"  - {r['query'][:70]}")
            if not r["routing_ok"]:
                print(f"    Routing: expected '{r['expected_agent']}', got '{r['actual_agent']}'")
            if not r["response_ok"]:
                print(f"    Response: missing expected keywords")
    print()


if __name__ == "__main__":
    evaluate()