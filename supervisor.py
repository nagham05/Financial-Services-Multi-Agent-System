from config import llm
from dotenv import load_dotenv
load_dotenv()

from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import HumanMessage, SystemMessage

from agents.sql_agent import sql_agent_node, sql_tools
from agents.rag_agent import rag_agent_node


class SupervisorState(TypedDict):
    messages: Annotated[list, add_messages] 
    next_agent: str

# simple supervisor node that routes to correct agent
def supervisor_node(state: SupervisorState):
    system = SystemMessage(content="""You are a supervisor that routes questions to the right agent.
    Reply with ONLY one word:
    - 'sql' if the question is about customer data, accounts, transactions, loans, or investments from the database
    - 'rag' if the question is about financial regulations, reports, Basel III, Federal Reserve, JPMorgan, or conflict economics
    """)
    
    response = llm.invoke([system] + state["messages"])
    return {"next_agent": response.content.strip().lower()}

def route_to_agent(state: SupervisorState):
    return state["next_agent"]


# build graph
graph = StateGraph(SupervisorState)
graph.add_node("supervisor", supervisor_node)
graph.add_node("sql_agent", sql_agent_node)
graph.add_node("sql_tools", ToolNode(sql_tools))
graph.add_node("rag_agent", rag_agent_node)

graph.add_edge(START, "supervisor")

graph.add_conditional_edges(
    "supervisor",
    route_to_agent,
    {
        "sql": "sql_agent",
        "rag": "rag_agent"
    }
)

graph.add_conditional_edges(
    "sql_agent",
    tools_condition,
    {
        "tools": "sql_tools",  # map default "tools" to your "sql_tools" node
        END: END
    }
)

graph.add_edge("sql_tools", "sql_agent")

graph.add_edge("rag_agent", END)

memory = MemorySaver()
app = graph.compile(checkpointer=memory)


if __name__ == "__main__":
    import uuid
    
    queries = [
         "What is the total balance across all active accounts?",  # SQL
        "What is the minimum capital requirement under Basel III?",  # RAG
        "How many customers have overdue loans?",  # SQL
        "What are the main vulnerabilities in the US financial system?",  # RA
    ]
    
    for query in queries:
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}

        print(f"\nUser: {query}")
        print("-" * 50)
        result = app.invoke(
            {"messages": [HumanMessage(content=query)]},
            config=config
        )
        print(f"Agent: {result['messages'][-1].content}")
        print("=" * 50)