import sys
from dotenv import load_dotenv
load_dotenv("../.env")

sys.path.append("..")

from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.utilities import SerpAPIWrapper
from config import llm
from concurrent.futures import ThreadPoolExecutor

web_search = SerpAPIWrapper()

def researcher_node(state):
    research_query = state["research_query"]
    
    # 2 targeted searches — original query + financial analysis angle
    queries = [research_query, f"{research_query} financial analysis"]
    
    all_results = []
    for query in queries:
        print(f"Searching: {query}")
        try:
            result = web_search.run(query)
            all_results.append(f"Search: {query}\nResults: {result}")
        except Exception as e:
            all_results.append(f"Search: {query}\nResults: Failed - {str(e)}")
    
    raw_research = "\n\n---\n\n".join(all_results)
    
    return {
        "raw_research": raw_research,
        "messages": [AIMessage(content=f"Research completed from {len(queries)} searches.")]
    }