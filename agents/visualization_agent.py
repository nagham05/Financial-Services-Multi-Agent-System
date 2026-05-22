import sys
import os
import re
import json
from dotenv import load_dotenv
load_dotenv("../.env")

sys.path.append("..")
from config import llm
from langchain_core.messages import AIMessage
from utils import run_sql_query


def generate_chart(user_query, sql_result, mapping):
    chart_type = mapping["chart_type"]
    x_col = mapping["x_column"]
    y_col = mapping["y_column"]
    title = mapping.get("title", "Chart")

    x_values = [str(row[x_col]) for row in sql_result]
    y_values = [float(row[y_col]) for row in sql_result]

    chartjs_type = {
        "bar": "bar",
        "line": "line",
        "pie": "pie",
        "scatter": "scatter",
        "histogram": "bar"
    }.get(chart_type, "bar")

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; }}
        .chart-container {{ width: 800px; height: 500px; margin: auto; }}
        h2 {{ text-align: center; color: #333; }}
    </style>
</head>
<body>
    <h2>{title}</h2>
    <div class="chart-container">
        <canvas id="myChart"></canvas>
    </div>
    <script>
        const ctx = document.getElementById('myChart').getContext('2d');
        new Chart(ctx, {{
            type: '{chartjs_type}',
            data: {{
                labels: {x_values},
                datasets: [{{
                    label: '{title}',
                    data: {y_values},
                    backgroundColor: [
                        'rgba(54, 162, 235, 0.6)',
                        'rgba(255, 99, 132, 0.6)',
                        'rgba(75, 192, 192, 0.6)',
                        'rgba(255, 206, 86, 0.6)',
                        'rgba(153, 102, 255, 0.6)',
                        'rgba(255, 159, 64, 0.6)',
                        'rgba(199, 199, 199, 0.6)',
                        'rgba(83, 102, 255, 0.6)'
                    ],
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 2,
                    fill: false
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ position: 'top' }},
                    title: {{
                        display: true,
                        text: '{title}'
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""

    os.makedirs("charts", exist_ok=True)
    chart_path = f"charts/{title.replace(' ', '_')}.html"
    with open(chart_path, "w") as f:
        f.write(html_content)

    return chart_path


def visualization_agent_node(state):
    user_query = state["messages"][-1].content

    # Step 1 — generate SQL
    sql_prompt = f"""Generate a PostgreSQL query for this visualization request.

    Database schema with EXACT column names:
    - customers (id, name, email, country, account_type)
    - accounts (id, customer_id, balance, currency, status) — customer_id references customers.id
    - transactions (id, account_id, type, amount, date, status) — account_id references accounts.id
    - loans (id, customer_id, amount, interest_rate, due_date, status) — customer_id references customers.id
    - investments (id, customer_id, asset_name, amount_invested, current_value, purchase_date) — customer_id references customers.id

    IMPORTANT — use EXACT column names:
    - investments table has: amount_invested, current_value, purchase_date (NOT date, NOT amount)
    - transactions table has: date (NOT purchase_date)
    - loans table has: due_date (NOT date)

    JOIN rules:
    - accounts + customers: JOIN customers c ON a.customer_id = c.id
    - transactions + customers: JOIN accounts a ON t.account_id = a.id JOIN customers c ON a.customer_id = c.id
    - loans + customers: JOIN customers c ON l.customer_id = c.id
    - investments + customers: JOIN customers c ON i.customer_id = c.id

    Return ONLY the raw SQL query, no markdown, no backticks, no explanation.
    Request: {user_query}"""

    sql_response = llm.invoke(sql_prompt)
    sql_query = sql_response.content.strip()
    # strip any accidental markdown fences
    sql_query = re.sub(r'```sql\s*', '', sql_query)
    sql_query = re.sub(r'```\s*', '', sql_query)
    sql_query = sql_query.strip()

    # Step 2 — execute SQL
    sql_result = run_sql_query(sql_query)

    if isinstance(sql_result, str) and "error" in sql_result.lower():
        return {"messages": [AIMessage(content=f"Database error: {sql_result}")]}

    if not sql_result or len(sql_result) == 0:
        return {"messages": [AIMessage(content="No data found for this query.")]}

    # Step 3 — determine chart config
    mapping_prompt = f"""You are a data visualization assistant.
    Given this user request and SQL results, determine the chart configuration.

    User request: {user_query}
    SQL results (first 3 rows): {sql_result[:3]}
    Available columns: {list(sql_result[0].keys())}

    Reply with ONLY a raw JSON object — no markdown, no backticks, no explanation:
    {{"chart_type": "bar", "x_column": "name", "y_column": "balance", "title": "Account Balances by Customer"}}
    """

    mapping_response = llm.invoke(mapping_prompt)
    raw = mapping_response.content.strip()

    # strip markdown fences if the LLM ignored instructions
    raw = re.sub(r'```json\s*', '', raw)
    raw = re.sub(r'```\s*', '', raw)
    raw = raw.strip()

    try:
        mapping = json.loads(raw)
    except json.JSONDecodeError as e:
        return {"messages": [AIMessage(content=f"Could not parse chart configuration: {e}\nRaw response: {raw}")]}

    # Step 4 — generate Chart.js HTML
    chart_path = generate_chart(user_query, sql_result, mapping)

    return {"messages": [AIMessage(content=f"Chart generated at: {chart_path} — open in browser to view.")]}