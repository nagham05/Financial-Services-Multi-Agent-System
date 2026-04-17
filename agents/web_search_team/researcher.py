import sys
from dotenv import load_dotenv
load_dotenv("../.env")

sys.path.append("..")

from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.tools import DuckDuckGoSearchRun
from config import llm

web_search = DuckDuckGoSearchRun(backend="lite")

def researcher_node(state):
    research_query = state["research_query"]
    
    # generate 3 different search queries for comprehensive research
    # why 3 queries? This allows the researcher to explore different angles and sources, increasing the chances of finding relevant information. 
    # It also helps avoid bias from a single query formulation and can uncover insights that might be missed with just one search.
    search_queries_prompt = f"""
    You are a financial research assistant. Generate 3 different search queries 
    to thoroughly research this topic: "{research_query}"
    
    Return ONLY a Python list of 3 search queries, nothing else.
    Example: ["query 1", "query 2", "query 3"]
    """
    
    # get the search queries from the LLM
    queries_response = llm.invoke([HumanMessage(content=search_queries_prompt)])
    
    # parse the queries 
    # why ast: Using ast.literal_eval allows us to safely parse the LLM's response as a Python list. 
    # It evaluates the string as a Python literal, which is more robust than trying to parse it manually or using regex. 
    # This way, we can ensure that we get a proper list of queries even if the formatting isn't perfect, and it prevents potential security issues from evaluating arbitrary code.
    import ast
    try:
        queries = ast.literal_eval(queries_response.content.strip())
    except:
        queries = [research_query]  # fallback to original query
    
    # run all searches and collect results
    all_results = []
    for query in queries:
        result = web_search.run(query)
        all_results.append(f"Search: {query}\nResults: {result}")
    
    raw_research = "\n\n---\n\n".join(all_results)
    
    return {
        "raw_research": raw_research,
        "messages": [AIMessage(content=f"Research completed. Found information from {len(queries)} searches.")]
    }