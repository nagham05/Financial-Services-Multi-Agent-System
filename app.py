import os
import uuid
import threading
import http.server
import socketserver
from dotenv import load_dotenv
load_dotenv()

import chainlit as cl
from langchain_core.messages import HumanMessage
from supervisor import app
from agents.rag_agent import DOCUMENT_NAMES, DOCUMENT_LINKS
from agents.doc_qa_agent import extract_text_from_pdf, is_financial_document, answer_from_document

# agent display config
AGENT_CONFIG = {
    "sql":          {"emoji": "🗄️",  "name": "SQL Agent",          "status": "Querying financial database..."},
    "rag":          {"emoji": "📚",  "name": "RAG Agent",           "status": "Searching financial documents..."},
    "conversation": {"emoji": "💬",  "name": "Conversation Agent",  "status": "Thinking..."},
    "visualization":{"emoji": "📊",  "name": "Visualization Agent", "status": "Generating chart..."},
    "web_research": {"emoji": "🌐",  "name": "Web Research Team",   "status": "Searching the web..."},
    "doc_qa":       {"emoji": "📄",  "name": "Document QA Agent",   "status": "Analyzing uploaded document..."},
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
    cl.user_session.set("uploaded_doc_text", None)
    cl.user_session.set("uploaded_doc_name", None)
    await cl.Message(
        content=(
            "👋 Welcome to the **Financial AI Assistant**!\n\n"
            "Ask me anything about your financial data, regulations, markets, or request a chart.\n\n"
            "📎 You can also **attach a PDF** to ask questions about it — I'll check if it's a financial document and answer accordingly."
        )
    ).send()

@cl.on_message
async def main(message: cl.Message):
    thread_id = cl.user_session.get("thread_id")
    config = {"configurable": {"thread_id": thread_id}}

    # ── Document upload handling ──────────────────────────────────────────────
    # Check if this message contains an uploaded file
    if message.elements:
        pdf_files = [el for el in message.elements if el.mime == "application/pdf" or (el.name and el.name.endswith(".pdf"))]

        if pdf_files:
            uploaded_file = pdf_files[0]
            agent = AGENT_CONFIG["doc_qa"]

            thinking_msg = cl.Message(
                content=f"{agent['emoji']} Routing to **{agent['name']}** — {agent['status']}"
            )
            await thinking_msg.send()

            # Extract text from uploaded PDF
            doc_text = await cl.make_async(extract_text_from_pdf)(uploaded_file.path)

            if doc_text.startswith("ERROR_READING_PDF"):
                error_detail = doc_text.replace("ERROR_READING_PDF: ", "")
                await cl.Message(
                    content=f"**{agent['emoji']} {agent['name']}**\n\n❌ Could not read the uploaded PDF: {error_detail}"
                ).send()
                return

            # Check if it's a financial document
            is_financial = await cl.make_async(is_financial_document)(doc_text)

            if not is_financial:
                await cl.Message(
                    content=(
                        f"**{agent['emoji']} {agent['name']}**\n\n"
                        "❌ This document does not appear to be a financial document. "
                        "I can only answer questions about financial documents such as annual reports, "
                        "bank statements, regulatory filings, investment reports, or economic research papers. "
                        "Please upload a financial document and try again."
                    )
                ).send()
                return

            # Store in session for follow-up questions
            cl.user_session.set("uploaded_doc_text", doc_text)
            cl.user_session.set("uploaded_doc_name", uploaded_file.name)

            # If the user also typed a question alongside the upload, answer it
            question = message.content.strip()
            if question:
                response = await cl.make_async(answer_from_document)(
                    question, doc_text, uploaded_file.name
                )
                await cl.Message(
                    content=f"**{agent['emoji']} {agent['name']}**\n\n{response}"
                ).send()
            else:
                await cl.Message(
                    content=(
                        f"**{agent['emoji']} {agent['name']}**\n\n"
                        f"✅ **{uploaded_file.name}** has been verified as a financial document and is ready for questions.\n\n"
                        "Go ahead and ask anything about this document!"
                    )
                ).send()
            return

    # ── Follow-up questions on a previously uploaded document ────────────────
    uploaded_doc_text = cl.user_session.get("uploaded_doc_text")
    uploaded_doc_name = cl.user_session.get("uploaded_doc_name")

    if uploaded_doc_text:
        # User has an active uploaded doc — check if they're asking about it
        # Heuristic: if the message doesn't look like a new routing keyword, answer from doc
        user_message_lower = message.content.lower()
        new_doc_triggers = ["forget", "clear", "remove document", "new document", "different doc"]

        if any(t in user_message_lower for t in new_doc_triggers):
            cl.user_session.set("uploaded_doc_text", None)
            cl.user_session.set("uploaded_doc_name", None)
            await cl.Message(
                content="🗑️ Uploaded document cleared. You can now ask general questions or upload a new document."
            ).send()
            return

        # Route to doc QA if a doc is active
        agent = AGENT_CONFIG["doc_qa"]
        thinking_msg = cl.Message(
            content=f"{agent['emoji']} Routing to **{agent['name']}** — answering from **{uploaded_doc_name}**..."
        )
        await thinking_msg.send()

        response = await cl.make_async(answer_from_document)(
            message.content, uploaded_doc_text, uploaded_doc_name
        )
        await cl.Message(
            content=f"**{agent['emoji']} {agent['name']}** *(from {uploaded_doc_name})*\n\n{response}"
        ).send()
        return

    # ── Normal routing (all existing logic untouched) ─────────────────────────
    user_message = message.content.lower()
    chart_keywords = ["chart", "graph", "plot", "pie", "bar", "line", "histogram", "scatter", "visuali", "show me"]

    if any(keyword in user_message for keyword in chart_keywords):
        agent_key = "visualization"
    elif any(word in user_message for word in ["latest", "current", "today", "news", "price", "recent", "now"]):
        agent_key = "web_research"
    elif any(word in user_message for word in ["what is", "explain", "how does", "difference between"]):
        agent_key = "conversation"
    elif any(word in user_message for word in ["basel", "federal reserve", "jpmorgan", "regulation", "war", "conflict"]):
        agent_key = "rag"
    else:
        agent_key = "sql"

    agent = AGENT_CONFIG.get(agent_key, AGENT_CONFIG["conversation"])

    # Step 2 — show routing message immediately
    thinking_msg = cl.Message(content=f"{agent['emoji']} Routing to **{agent['name']}** — {agent['status']}")
    await thinking_msg.send()

    # Step 3 — invoke LangGraph
    result = await cl.make_async(app.invoke)(
        {"messages": [HumanMessage(content=message.content)]},
        config=config
    )

    # Step 4 — get actual agent used from result
    actual_agent_key = result.get("next_agent", agent_key)
    actual_agent = AGENT_CONFIG.get(actual_agent_key, agent)

    # update if routing changed
    if actual_agent_key != agent_key:
        thinking_msg.content = f"{actual_agent['emoji']} Routed to **{actual_agent['name']}** — {actual_agent['status']}"
        await thinking_msg.update()

    # get final response
    response = result["messages"][-1].content

    if "charts/" in response and ".html" in response:
        import re
        match = re.search(r'charts/[^\s]+\.html', response)
        if match:
            chart_path = match.group(0)
            chart_url = f"http://localhost:8080/{chart_path}"
            await cl.Message(
                content=f"**{actual_agent['emoji']} {actual_agent['name']}**\n\n📊 Chart ready! [Click here to view]({chart_url})"
            ).send()
    elif actual_agent_key == "rag":
        # add source links at the bottom
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