import sys
import os
import json
from dotenv import load_dotenv
load_dotenv("../.env")

sys.path.append("..")
from config import llm
import matplotlib
matplotlib.use('Agg')  # non-interactive backend for saving files
import matplotlib.pyplot as plt
from langchain_core.messages import AIMessage
from utils import run_sql_query

# This function generates a chart based on the SQL results and the user's original query. 
# It uses the LLM to determine the best chart type and which columns to use for the axes, then creates and saves the chart using matplotlib.
def generate_chart(user_query, sql_result):
    if not sql_result or sql_result == "No results found.":
        return "No data available to generate chart."

    # LLM determines chart type and column mapping
    mapping_prompt = f"""
    You are a data visualization assistant.
    Given this user request and SQL results, determine:
    1. The best chart type (bar, line, pie, scatter, histogram)
    2. Which columns to use for x-axis and y-axis/labels

    User request: {user_query}
    SQL results (first 3 rows): {sql_result[:3]}
    Available columns: {list(sql_result[0].keys())}

    Reply with ONLY a JSON object like this:
    {{"chart_type": "bar", "x_column": "name", "y_column": "balance", "title": "Account Balances by Customer"}}
    """
    
    mapping_response = llm.invoke(mapping_prompt)
    
    try:
        mapping = json.loads(mapping_response.content.strip())
        chart_type = mapping["chart_type"]
        x_col = mapping["x_column"]
        y_col = mapping["y_column"]
        title = mapping.get("title", "Chart")
    except:
        return "Could not determine chart configuration."

    # extract data
    x_values = [row[x_col] for row in sql_result]
    y_values = [row[y_col] for row in sql_result]

    plt.figure(figsize=(10, 6))
    
    if chart_type == "bar":
        plt.bar(x_values, y_values)
        plt.xlabel(x_col)
        plt.ylabel(y_col)
    elif chart_type == "line":
        plt.plot(x_values, y_values)
        plt.xlabel(x_col)
        plt.ylabel(y_col)
    elif chart_type == "pie":
        plt.pie(y_values, labels=x_values, autopct='%1.1f%%')
    elif chart_type == "scatter":
        plt.scatter(x_values, y_values)
        plt.xlabel(x_col)
        plt.ylabel(y_col)
    elif chart_type == "histogram":
        plt.hist(y_values, bins=10)
        plt.xlabel(y_col)
        plt.ylabel("Frequency")

    plt.title(title)
    plt.tight_layout()

    # save chart
    os.makedirs("charts", exist_ok=True)
    chart_path = f"charts/{title.replace(' ', '_')}.png"
    plt.savefig(chart_path)
    plt.close()

    return chart_path

# This is the main function for the visualization agent. 
# It takes the user's natural language query, generates a SQL query using the LLM, executes it against the database, 
# and then generates a chart based on the results.
def visualization_agent_node(state):
    user_query = state["messages"][-1].content

    # Step 1 — LLM generates SQL from natural language
    sql_prompt = f"""Generate a PostgreSQL query for this visualization request.

    Database schema:
    - customers (id, name, email, country, account_type)
    - accounts (id, customer_id, balance, currency, status) — customer_id references customers.id
    - transactions (id, account_id, type, amount, date, status) — account_id references accounts.id
    - loans (id, customer_id, amount, interest_rate, due_date, status) — customer_id references customers.id
    - investments (id, customer_id, asset_name, amount_invested, current_value) — customer_id references customers.id

    JOIN rules:
    - To get customer names with accounts: JOIN customers c ON a.customer_id = c.id
    - To get customer names with transactions: JOIN accounts a ON t.account_id = a.id JOIN customers c ON a.customer_id = c.id
    - To get customer names with loans: JOIN customers c ON l.customer_id = c.id
    - To get customer names with investments: JOIN customers c ON i.customer_id = c.id

    Return ONLY the raw SQL query with no markdown, no backticks, no ```sql blocks.
    Request: {user_query}"""
    
    sql_response = llm.invoke(sql_prompt)
    sql_query = sql_response.content.strip()
    
    # remove markdown code blocks if LLM adds them
    import re
    sql_query = re.sub(r'```sql\s*', '', sql_query)
    sql_query = re.sub(r'```\s*', '', sql_query)
    sql_query = sql_query.strip()

    # Step 2 — execute SQL
    sql_result = run_sql_query(sql_query)

    if isinstance(sql_result, str) and "error" in sql_result.lower():
        return {"messages": [AIMessage(content=f"Database error: {sql_result}")]}

    # Step 3 — generate chart
    chart_path = generate_chart(user_query, sql_result)

    if chart_path.startswith("charts/"):
        return {"messages": [AIMessage(content=f"Chart generated and saved at: {chart_path}")]}
    
    return {"messages": [AIMessage(content=chart_path)]}