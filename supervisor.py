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
        Reply with ONLY one word:
        - 'sql' if the question is about querying specific data from the database (counts, totals, lists, lookups)
        - 'rag' if the question is about financial regulations, reports, Basel III, Federal Reserve, JPMorgan, or conflict economics
        - 'conversation' if the question is about general financial concepts, definitions, or explanations
        - 'visualization' if the question explicitly mentions a chart, graph, plot, pie chart, bar chart, line chart, or any visual representation of data
        - 'web_research' if the question asks about current events, latest news, live prices, or recent trends

        IMPORTANT:
            -  If the user mentions ANY visual format (chart, graph, plot, visualization), ALWAYS route to 'visualization' regardless of the data type.
            - If the question is about war, conflict, or geopolitical effects on economy → ALWAYS route to 'rag'

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
        "tools": "sql_tools",  # map default "tools" to your "sql_tools" node
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

 
#         "What is the total balance across all active accounts?",          # sql
#         "What is the minimum capital requirement under Basel III?",        # rag
#         "What is compound interest?",                                      # conversation
#         "Show me a bar chart of account balances by customer",            # visualization
#         "Create a line graph of monthly transaction volumes for the past year." , # visualization
#         "Show me a line chart of loan amounts by customer"
#         #"Show me a pie chart of loan status distribution"
#         "What are the latest news about the Federal Reserve interest rates?", # web search
#         "What are the latest trends in AI investment in 2025?",
#         "What is the current price of gold?"
    

if __name__ == "__main__":
    import uuid
    
    
    while True:
        thread_id = str(uuid.uuid4())  # one thread per conversation
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