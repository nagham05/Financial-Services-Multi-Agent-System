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
from agents.conversation_agent import conversation_agent_node
from agents.visualization_agent import visualization_agent_node
from agents.web_search_team.sub_supervisor import web_research_node

class SupervisorState(TypedDict):
    messages: Annotated[list, add_messages] 
    next_agent: str

# simple supervisor node that routes to correct agent
def supervisor_node(state: SupervisorState):
    system = SystemMessage(content="""You are a supervisor that routes questions to the right agent.
        Reply with ONLY one word — no punctuation, no explanation.

        Agents:
        - 'sql'          → the user wants specific data from the database: a number, a list, a lookup, a count, a total, a ranking.
                           Examples: "who has the highest loan?", "list all active accounts", "how many customers are in the US?"
        - 'rag'          → the question is about financial regulations, frameworks, or documents: Basel III, Federal Reserve reports, JPMorgan annual report, IMF, conflict economics.
                           Examples: "what does Basel III say about capital buffers?", "Fed funding risk assessment", "economic impact of war"
        - 'conversation' → the user is asking for a definition, explanation, or concept in general finance — NOT about our database.
                           Examples: "what is a bear market?", "explain compound interest", "what is inflation?", "how does a hedge fund work?"
        - 'visualization'→ the user explicitly asks for a chart, graph, plot, or visual representation of data.
                           Examples: "pie chart of customers by region", "bar chart of loan amounts", "show me a graph of balances"
        - 'web_research' → the user wants current/live information: prices, news, recent events, today's rates.
                           Examples: "gold price today", "latest Fed interest rate decision", "recent news about Tesla"

        STRICT RULES — follow these exactly:
        1. If the question asks "what is X", "explain X", "define X", or "how does X work" for any financial concept → ALWAYS 'conversation'. Never 'sql'.
        2. If the question mentions ANY visual format (chart, graph, plot, pie, bar, line) → ALWAYS 'visualization'.
        3. If the question is about war, conflict, geopolitical risk, or named financial documents/frameworks → ALWAYS 'rag'.
        4. If the question asks for live/current data or news → ALWAYS 'web_research'.
        5. Only use 'sql' when the user clearly wants a specific value or list FROM THE DATABASE.
        6. When in doubt → 'conversation'.
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
graph.add_node("conversation_agent", conversation_agent_node)
graph.add_node("visualization_agent", visualization_agent_node)
graph.add_node("web_research", web_research_node)

graph.add_edge(START, "supervisor")

graph.add_conditional_edges(
    "supervisor",
    route_to_agent,
    {
        "sql": "sql_agent",
        "rag": "rag_agent",
        "conversation": "conversation_agent",
        "visualization": "visualization_agent",
        "web_research": "web_research"
    }
)

graph.add_conditional_edges(
    "sql_agent",
    tools_condition,
    {
        "tools": "sql_tools",
        END: END
    }
)

graph.add_edge("sql_tools", "sql_agent")

graph.add_edge("rag_agent", END)
graph.add_edge("conversation_agent", END)
graph.add_edge("visualization_agent", END)
graph.add_edge("web_research", END)

memory = MemorySaver()
app = graph.compile(checkpointer=memory)


if __name__ == "__main__":
    import uuid
    
    while True:
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}

        user_input = input("User: ").strip()
        if user_input.lower() in ["exit", "quit"]:
            print("Exiting the agent. Goodbye!")
            break
        
        if not user_input:
            continue
        
        result = app.invoke(
            {"messages": [HumanMessage(content=user_input)], "query": user_input},
            config=config
        )
        print(f"Agent: {result['messages'][-1].content}\n")