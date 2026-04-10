import sys
from dotenv import load_dotenv
load_dotenv("../.env")

sys.path.append("..")

from config import llm
from langchain_core.messages import SystemMessage, AIMessage

# system prompt
system_prompt = SystemMessage(content="""
                    You are a helpful and professional financial assistant specializing in general financial concepts.
                    Answer questions based on your knowledge — do not make up specific data or statistics.
                    If asked about specific company data or regulations, suggest the user ask the SQL or document agent instead.
                    If you don't know the answer, say 'I don't have that information.'
                    Keep answers clear, concise and professional.
                """)

def conversation_agent_node(state):
    # prepend system prompt to conversation history
    response = llm.invoke([system_prompt] + state["messages"])
    return {"messages": [AIMessage(content=response.content)]}