import sys
import fitz  # PyMuPDF — already installed per project requirements
from dotenv import load_dotenv
load_dotenv("../.env")

sys.path.append("..")
from config import llm
from langchain_core.messages import AIMessage

# Max characters to send to the LLM (avoid token overflow for large PDFs)
MAX_DOC_CHARS = 12000


def extract_text_from_pdf(file_path: str) -> str:
    """Extract plain text from a PDF using PyMuPDF."""
    text = ""
    try:
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text()
        doc.close()
    except Exception as e:
        text = f"ERROR_READING_PDF: {str(e)}"
    return text


def is_financial_document(text: str) -> bool:
    """
    Ask the LLM to classify whether the extracted text is financial in nature.
    Returns True if financial, False otherwise.
    """
    # Send a short sample to keep classification fast and cheap
    sample = text[:3000]

    classification_prompt = f"""You are a document classifier. Read the following document excerpt and decide if it is a financial document.

A financial document includes: annual reports, bank statements, financial statements, investment reports, loan agreements, regulatory filings, economic research papers, earnings reports, budget documents, insurance policies, tax documents, financial regulations, or any document primarily about money, finance, economics, or financial markets.

Reply with ONLY one word: YES or NO.

Document excerpt:
{sample}"""

    response = llm.invoke(classification_prompt)
    answer = response.content.strip().upper()
    return answer.startswith("YES")


def answer_from_document(question: str, doc_text: str, filename: str) -> str:
    """
    Answer the user's question using only the content of the uploaded document.
    """
    # Truncate to avoid token limits
    context = doc_text[:MAX_DOC_CHARS]
    if len(doc_text) > MAX_DOC_CHARS:
        context += "\n\n[Note: Document was truncated due to length. Only the first portion was used.]"

    qa_prompt = f"""You are a senior financial analyst assistant. Answer the user's question using ONLY the content of the uploaded document below.

Guidelines:
- Base your answer strictly on the document content
- If the answer is not found in the document, say "I could not find this information in the uploaded document."
- Include specific numbers, percentages, and figures when available
- Be concise and professional
- Always refer to the document as "{filename}"

Document Content:
{context}

User Question: {question}"""

    response = llm.invoke(qa_prompt)
    return response.content


def doc_qa_agent_node(state: dict) -> dict:
    """
    LangGraph-compatible agent node for uploaded document Q&A.
    
    Expects state to include:
      - messages: conversation history (last message = user question)
      - uploaded_doc_text: extracted text from the uploaded PDF
      - uploaded_doc_name: filename of the uploaded PDF
    """
    question = state["messages"][-1].content
    doc_text = state.get("uploaded_doc_text", "")
    doc_name = state.get("uploaded_doc_name", "uploaded document")

    if not doc_text or doc_text.startswith("ERROR_READING_PDF"):
        error = doc_text.replace("ERROR_READING_PDF: ", "") if doc_text else "No document content found."
        return {"messages": [AIMessage(content=f"❌ Could not read the uploaded document: {error}")]}

    # Check if the document is financial
    if not is_financial_document(doc_text):
        return {
            "messages": [AIMessage(
                content=(
                    "❌ This document does not appear to be a financial document. "
                    "I can only answer questions about financial documents such as annual reports, "
                    "bank statements, regulatory filings, investment reports, or economic research papers. "
                    "Please upload a financial document and try again."
                )
            )]
        }

    # Answer the question from the document
    answer = answer_from_document(question, doc_text, doc_name)
    return {"messages": [AIMessage(content=answer)]}