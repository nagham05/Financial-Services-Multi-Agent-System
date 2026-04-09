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

# Define the prompt template
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", """You are a senior financial analyst assistant. Answer questions using ONLY the provided context from financial documents.

        Guidelines:
        - Use ALL provided context to answer, even if the answer requires combining information from multiple documents
        - Only synthesize across documents when there is EXPLICIT evidence in BOTH sources — never infer relationships that are not directly stated
        - If the answer requires inference rather than direct quotes, prefix with "Based on available context, it appears that..."
        - If the answer truly cannot be found or inferred from the context, say 'I could not find this in the provided documents.'
        - Always cite which document your answer comes from using the document name in brackets
        - Include specific numbers, percentages, and figures when available
        - Never make up financial data or statistics
        - If combining information from multiple documents, clearly state which fact came from which document
        - Keep answers professional and concise

        Context: {context}"""),
                ("human", "{question}")
    ]
)


# Helper function to format retrieved documents for the prompt
def format_docs(docs):
    return "\n\n".join([f"[{doc.metadata.get('topic', 'unknown')}]\n{doc.page_content}" for doc in docs])


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

