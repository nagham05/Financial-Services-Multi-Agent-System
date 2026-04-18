import sys
from dotenv import load_dotenv
load_dotenv("../.env")

sys.path.append("..")

from langchain_core.messages import HumanMessage, AIMessage
from config import llm

def report_writer_node(state):
    report_prompt = f"""
   You are a senior financial analyst assistant.
    
    Original Question: {state["research_query"]}
    Raw Research: {state["raw_research"]}
    
    Based on the nature of the question, choose the appropriate response format:
    
    - If the question asks for a SPECIFIC FACT (price, rate, number, date) → give a direct 1-2 sentence answer
    - If the question asks for NEWS or RECENT EVENTS → give a brief 3-5 bullet point summary
    - If the question asks for ANALYSIS or TRENDS → give a structured report with:
        * Executive Summary
        * Key Findings
        * Market Implications
        * Conclusion
    
    Always be concise and professional. Never use a long format when a short answer suffices.
    """

    response = llm.invoke([HumanMessage(content=report_prompt)])
    return {
        "final_report": response.content,
        "messages": [AIMessage(content="Report writing completed.")]
    }