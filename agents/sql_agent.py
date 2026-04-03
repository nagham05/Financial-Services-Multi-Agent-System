from dotenv import load_dotenv
load_dotenv()

from config import llm
from langchain_core.tools import tool
import psycopg2
from langchain_core.messages import HumanMessage, SystemMessage

@tool
def execute_sql_query(query: str) -> str:
    """Use this tool to query the financial database.
    Available tables:
    - customers (id, name, email, country, account_type)
    - accounts (id, customer_id, balance, currency, status)
    - transactions (id, account_id, type, amount, date, status)
    - loans (id, customer_id, amount, interest_rate, due_date, status)
    - investments (id, customer_id, asset_name, amount_invested, current_value)
    Input must be a valid PostgreSQL query."""

    try: 
        conn = psycopg2.connect(
            host="localhost",
            database="financial_db",
            user="financial_user",
            password="financial-agent"
        )
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()

        # get column names
        columns = [description[0] for description in cursor.description]
        conn.close()
        
        if not results:
            return "No results found."
        
        # format results with column names
        formatted = [dict(zip(columns, row)) for row in results]
        return str(formatted)
    except Exception as e:
        return f"Database error: {str(e)}"
    


def sql_agent_node(state):
    system_prompt = SystemMessage(content="""You are a financial database expert. 
    When asked about financial data, always use the execute_sql_query tool to query the database.
    Write accurate PostgreSQL queries based on the user's question.
    After getting the results, explain them clearly in natural language.
    Always include relevant numbers and figures in your response.""")
    
    llm_with_tools = llm.bind_tools([execute_sql_query])
    
    response = llm_with_tools.invoke([system_prompt] + state["messages"])
    return {"messages": [response]}


sql_tools = [execute_sql_query]
