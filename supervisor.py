from config import llm
from dotenv import load_dotenv
load_dotenv()

from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import HumanMessage

from agents.sql_agent import sql_agent_node, sql_tools



class SupervisorState(TypedDict):
    messages: Annotated[list, add_messages] 


# build graph
graph = StateGraph(SupervisorState)

graph.add_node("sql_agent", sql_agent_node)
graph.add_node("sql_tools", ToolNode(sql_tools))

graph.add_edge(START, "sql_agent")

graph.add_conditional_edges(
    "sql_agent",
    tools_condition,
    {
        "tools": "sql_tools",  # map default "tools" to your "sql_tools" node
        END: END
    }
)

graph.add_edge("sql_tools", "sql_agent")

memory = MemorySaver()
app = graph.compile(checkpointer=memory)


if __name__ == "__main__":
    import uuid
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    
    queries = [
        "What is the total balance across all active accounts?",
        "How many customers have overdue loans?",
        "Show me all completed transactions"
    ]
    
    for query in queries:
        print(f"\nUser: {query}")
        print("-" * 50)
        result = app.invoke(
            {"messages": [HumanMessage(content=query)]},
            config=config
        )
        print(f"Agent: {result['messages'][-1].content}")
        print("=" * 50)