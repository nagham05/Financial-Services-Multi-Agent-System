import sys
from dotenv import load_dotenv
load_dotenv("../.env")

sys.path.append("..")

from langchain_core.messages import HumanMessage, AIMessage
from config import llm

def report_writer_node(state):
    report_prompt = f"""
    You are a senior financial analyst. 
    Convert the following raw research into a professional financial report.

    Original Question: {state["research_query"]}
    Raw Research: {state["raw_research"]}

    Structure the report with these sections:
    - Executive Summary
    - Key Findings  
    - Market Implications
    - Conclusion

    Keep it professional, concise, and factual.
    """

    response = llm.invoke([HumanMessage(content=report_prompt)])
    return {
        "final_report": response.content,
        "messages": [AIMessage(content="Report writing completed.")]
    }