import sys
from dotenv import load_dotenv
load_dotenv("../.env")

sys.path.append("..")

from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage

from agents.web_search_team.researcher import researcher_node
from agents.web_search_team.report_writer import report_writer_node

# state for web research subgraph
class WebResearchState(TypedDict):
    messages: Annotated[list, add_messages]
    research_query: str
    raw_research: str
    final_report: str

# routing function — if raw_research exists go to writer, else go to researcher
def route_web_research(state: WebResearchState):
    if state.get("raw_research"):
        return "report_writer"
    return "researcher"

# build subgraph
graph = StateGraph(WebResearchState)

graph.add_node("researcher", researcher_node)
graph.add_node("report_writer", report_writer_node)

graph.add_edge(START, "researcher")  # always start with researcher
graph.add_edge("researcher", "report_writer")  # then go to report writer
graph.add_edge("report_writer", END)  # then end

memory = MemorySaver()
web_research_app = graph.compile(checkpointer=memory)

# node function to use in main supervisor
def web_research_node(state):
    import uuid
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    
    query = state["messages"][-1].content
    
    result = web_research_app.invoke(
        {"research_query": query, "messages": state["messages"]},
        config=config
    )
    
    return {"messages": [AIMessage(content=result["final_report"])]}