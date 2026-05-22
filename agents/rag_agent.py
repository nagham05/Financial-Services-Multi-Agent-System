import os
from dotenv import load_dotenv
load_dotenv("../.env")

import sys
sys.path.append("..")  # go up one level to find config.py

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from config import llm

# embedding model
embeddings = HuggingFaceEmbeddings(
    model_name = "sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs = {"device": "cpu"},
    encode_kwargs = {"normalize_embeddings": True}
)

# get the absolute path of rag_agent.py's directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# build absolute path to faiss_index
FAISS_PATH = os.path.join(BASE_DIR, "..", "database", "faiss_index")

# load the saved index
vectorstore = FAISS.load_local(FAISS_PATH, embeddings, allow_dangerous_deserialization=True)

# create retriever — fetch top 8 most relevant chunks
retriever = vectorstore.as_retriever(search_kwargs={"k": 8})

# docs names and links for citation in answers
DOCUMENT_NAMES = {
    "jpmorgan_annual_report_2023": "JPMorgan Chase Annual Report 2023",
    "fed_financial_stability_2024": "Federal Reserve Financial Stability Report 2024",
    "basel_iii_framework": "Basel III Framework (BIS)",
    "imf_macroeconomic_costs_conflict": "IMF — Macroeconomic Costs of Conflict",
    "imf_geopolitical_risks_2025": "IMF — Geopolitical Risks 2025"
}

DOCUMENT_LINKS = {
    "jpmorgan_annual_report_2023": "https://www.jpmorganchase.com/content/dam/jpmc/jpmorgan-chase-and-co/investor-relations/documents/annualreport-2023.pdf",
    "fed_financial_stability_2024": "https://www.federalreserve.gov/publications/files/financial-stability-report-20241122.pdf",
    "basel_iii_framework": "https://www.bis.org/publ/bcbs189.pdf",
    "imf_macroeconomic_costs_conflict": "https://www.imf.org/-/media/files/publications/wp/2020/english/wpiea2020110-print-pdf.ashx",
    "imf_geopolitical_risks_2025": "https://www.imf.org/-/media/files/publications/gfsr/2025/april/english/ch2.pdf"
}

# Define the prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a senior financial analyst assistant. Answer questions using ONLY the provided context from financial documents.

    Guidelines:
    - Use ALL provided context to answer
    - Only synthesize across documents when there is EXPLICIT evidence in BOTH sources
    - If the answer requires inference, prefix with "Based on available context, it appears that..."
    - If not found, say 'I could not find this in the provided documents.'
    - Always cite which document your answer comes from using the full document name
    - Include specific numbers, percentages, and figures when available
    - Never make up financial data or statistics

    Context: {context}"""),
        ("human", "{question}")
])


# Helper function to format retrieved documents for the prompt
def format_docs(docs):
    return "\n\n".join([
        f"[{DOCUMENT_NAMES.get(doc.metadata.get('topic', 'unknown'), doc.metadata.get('topic', 'unknown'))}]\n{doc.page_content}" 
        for doc in docs
    ])

# Build the RAG chain
chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)


def rag_agent_node(state):
    question = state["messages"][-1].content
    response = chain.invoke(question)
    return {"messages": [AIMessage(content=response)]}

vectorstore = vectorstore  # expose for testing and potential future use

