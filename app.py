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

# agent display config
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

    # show thinking indicator
    thinking_msg = cl.Message(content="⚡ Analyzing your query...")
    await thinking_msg.send()

    # invoke LangGraph
    result = await cl.make_async(app.invoke)(
        {"messages": [HumanMessage(content=message.content)]},
        config=config
    )

    # get which agent was used
    agent_key = result.get("next_agent", "conversation")
    agent = AGENT_CONFIG.get(agent_key, AGENT_CONFIG["conversation"])

    # update thinking message
    thinking_msg.content = f"{agent['emoji']} Routed to **{agent['name']}** — {agent['status']}"
    await thinking_msg.update()

    # get final response
    response = result["messages"][-1].content

    # check if response is a chart path
    if "charts/" in response and ".html" in response:
            import re
            match = re.search(r'charts/[^\s]+\.html', response)
            if match:
                chart_path = match.group(0)
                chart_url = f"http://localhost:8080/{chart_path}"
                await cl.Message(
                    content=f"**{agent['emoji']} {agent['name']}**\n\n📊 Chart ready! [Click here to view]({chart_url})"
                ).send()
    else:
        await cl.Message(
            content=f"**{agent['emoji']} {agent['name']}**\n\n{response}"
            ).send()