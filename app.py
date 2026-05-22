import os
import re
import uuid
import threading
import http.server
import socketserver
from dotenv import load_dotenv
load_dotenv()

import chainlit as cl
from langchain_core.messages import HumanMessage, SystemMessage
from supervisor import app
from agents.rag_agent import DOCUMENT_NAMES, DOCUMENT_LINKS
from config import llm


# ── document attachment helpers ──────────────────────────────────────────────

def extract_text_from_file(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        try:
            import fitz
            doc = fitz.open(path)
            return "\n".join(page.get_text() for page in doc)
        except Exception as e:
            return f"[PDF extraction error: {e}]"
    elif ext in (".txt", ".md", ".csv"):
        with open(path, "r", errors="ignore") as f:
            return f.read()
    return ""


def is_financial_document(text: str) -> bool:
    sample = text[:3000]
    check = llm.invoke([
        SystemMessage(content=(
            "You are a document classifier. Reply with ONLY 'yes' or 'no'. "
            "Answer 'yes' if the document is related to finance, economics, banking, "
            "investments, regulations, financial markets, or accounting. "
            "Answer 'no' otherwise."
        )),
        HumanMessage(content=f"Is this a financial document?\n\n{sample}")
    ])
    return check.content.strip().lower().startswith("yes")


def answer_from_document(doc_text: str, question: str) -> str:
    context = doc_text[:6000]
    response = llm.invoke([
        SystemMessage(content=(
            "You are a senior financial analyst assistant. "
            "Answer the user's question using ONLY the provided document context. "
            "If the answer cannot be found in the document, say so clearly. "
            "Be concise and professional. Include relevant figures when available."
        )),
        HumanMessage(content=f"Document context:\n{context}\n\nQuestion: {question}")
    ])
    return response.content


def run_graph_with_status(user_input: str, config: dict):
    """
    Stream the LangGraph execution so we can:
      1. Detect when the supervisor node finishes → we know the agent name early
      2. Collect the final result after all nodes finish
    Returns (agent_key, final_result).
    """
    agent_key = "conversation"  # safe default
    final_result = None

    for chunk in app.stream(
        {"messages": [HumanMessage(content=user_input)]},
        config=config,
        stream_mode="updates",  # yields {node_name: state_update} after each node
    ):
        for node_name, state_update in chunk.items():
            if node_name == "supervisor":
                # supervisor just finished — routing decision is ready
                agent_key = state_update.get("next_agent", agent_key)
            # keep overwriting so final_result is the last complete state
            final_result = state_update

    return agent_key, final_result


# ── agent display config ─────────────────────────────────────────────────────

AGENT_CONFIG = {
    "sql":          {"emoji": "🗄️",  "name": "SQL Agent",          "status": "Querying financial database..."},
    "rag":          {"emoji": "📚",  "name": "RAG Agent",           "status": "Searching financial documents..."},
    "conversation": {"emoji": "💬",  "name": "Conversation Agent",  "status": "Thinking..."},
    "visualization":{"emoji": "📊",  "name": "Visualization Agent", "status": "Generating chart..."},
    "web_research": {"emoji": "🌐",  "name": "Web Research Team",   "status": "Searching the web..."},
}


def start_chart_server():
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", 8080), handler) as httpd:
        httpd.serve_forever()


@cl.on_app_startup
async def startup():
    thread = threading.Thread(target=start_chart_server, daemon=True)
    thread.start()


@cl.on_chat_start
async def start():
    thread_id = str(uuid.uuid4())
    cl.user_session.set("thread_id", thread_id)
    await cl.Message(
        content="👋 Welcome to the **Financial AI Assistant**!\n\nAsk me anything about your financial data, regulations, markets, or request a chart."
    ).send()


@cl.on_message
async def main(message: cl.Message):
    thread_id = cl.user_session.get("thread_id")
    config = {"configurable": {"thread_id": thread_id}}

    # ── handle file attachments ──────────────────────────────────────────────
    if message.elements:
        for element in message.elements:
            if not isinstance(element, cl.File):
                continue

            await cl.Message(content="📎 Processing your document...").send()
            doc_text = extract_text_from_file(element.path)

            if not doc_text.strip():
                await cl.Message(
                    content="⚠️ Could not extract text from the uploaded file. Please upload a readable PDF or text file."
                ).send()
                return

            financial = await cl.make_async(is_financial_document)(doc_text)

            if not financial:
                await cl.Message(
                    content="❌ This doesn't appear to be a financial document. I can only answer questions about financial, economic, banking, or investment documents."
                ).send()
                return

            question = message.content.strip() or "Summarize this document."
            await cl.Message(content="📄 Financial document detected — analysing your question...").send()
            answer = await cl.make_async(answer_from_document)(doc_text, question)
            await cl.Message(content=f"**📄 Document Agent**\n\n{answer}").send()
            return
    # ────────────────────────────────────────────────────────────────────────

    # Step 1 — show thinking message immediately
    thinking_msg = cl.Message(content="🤔 Thinking...")
    await thinking_msg.send()

    # Step 2 — stream the graph; update the thinking message as soon as routing is known
    agent_key = "conversation"
    final_messages = None

    def stream_graph():
        nonlocal agent_key, final_messages
        for chunk in app.stream(
            {"messages": [HumanMessage(content=message.content)]},
            config=config,
            stream_mode="updates",
        ):
            for node_name, state_update in chunk.items():
                if node_name == "supervisor":
                    # routing decided — update UI immediately (scheduled below)
                    agent_key = state_update.get("next_agent", agent_key)
                if "messages" in state_update and state_update["messages"]:
                    final_messages = state_update["messages"]

    # run the blocking stream in a thread so we can await UI updates mid-stream
    import asyncio

    loop = asyncio.get_event_loop()

    # we need a way to update the UI from inside the sync thread — use a queue
    routing_done = asyncio.Event()

    def stream_with_signal():
        nonlocal agent_key, final_messages
        for chunk in app.stream(
            {"messages": [HumanMessage(content=message.content)]},
            config=config,
            stream_mode="updates",
        ):
            for node_name, state_update in chunk.items():
                if node_name == "supervisor":
                    agent_key = state_update.get("next_agent", agent_key)
                    # signal the async side that routing is ready
                    loop.call_soon_threadsafe(routing_done.set)
                if "messages" in state_update and state_update["messages"]:
                    final_messages = state_update["messages"]

    # start the graph stream in a background thread
    stream_future = loop.run_in_executor(None, stream_with_signal)

    # wait for routing decision, then update the thinking message
    await routing_done.wait()
    actual_agent = AGENT_CONFIG.get(agent_key, AGENT_CONFIG["conversation"])
    thinking_msg.content = f"{actual_agent['emoji']} **{actual_agent['name']}** — {actual_agent['status']}"
    await thinking_msg.update()

    # wait for the full graph to finish
    await stream_future

    # Step 3 — send the final response
    if not final_messages:
        await cl.Message(content="⚠️ No response was generated.").send()
        return

    response = final_messages[-1].content

    if actual_agent["name"] == "Visualization Agent" and "charts/" in response and ".html" in response:
        match = re.search(r'charts/[^\s]+\.html', response)
        if match:
            chart_path = match.group(0)
            chart_url = f"http://localhost:8080/{chart_path}"
            await cl.Message(
                content=f"**{actual_agent['emoji']} {actual_agent['name']}**\n\n📊 Chart ready! [Click here to view]({chart_url})"
            ).send()
        else:
            await cl.Message(content=f"**{actual_agent['emoji']} {actual_agent['name']}**\n\n{response}").send()
    elif agent_key == "rag":
        source_links = "\n\n**📄 Sources:**\n"
        for key, name in DOCUMENT_NAMES.items():
            if key in response.lower() or name.lower() in response.lower():
                source_links += f"- [{name}]({DOCUMENT_LINKS[key]})\n"
        await cl.Message(
            content=f"**{actual_agent['emoji']} {actual_agent['name']}**\n\n{response}{source_links}"
        ).send()
    else:
        await cl.Message(
            content=f"**{actual_agent['emoji']} {actual_agent['name']}**\n\n{response}"
        ).send()