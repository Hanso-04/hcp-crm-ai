"""
The agent graph:

    START -> agent -> (tools_condition) -> tools -> agent -> ... -> END

`agent` is the Groq LLM with the 5 tools bound to it (tool-calling / ReAct
loop). `tools` executes whichever tool(s) the model chose via LangGraph's
prebuilt ToolNode, which also handles our `Command`-based state updates.
The loop continues until the model responds with no further tool calls.
"""

from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from app.agent.llm import get_llm
from app.agent.state import AgentState
from app.agent.tools import ALL_TOOLS

SYSTEM_PROMPT = SystemMessage(content="""You are the AI assistant embedded in a
pharma field rep's CRM "Log HCP Interaction" screen. The structured form on
screen can ONLY be filled or corrected by you calling your tools — the rep
cannot type into it directly, so treat every message as something to act on.

Rules:
- A new interaction description -> call log_interaction.
- A correction to something already logged -> call edit_interaction (patch
  only the mentioned field(s), never re-log the whole thing).
- If the rep names an HCP and no history has been fetched yet in this
  conversation, call fetch_hcp_history first so you have context.
- After logging or editing content that describes the clinical conversation,
  call compliance_sentiment_flag to check sentiment and compliance risk.
- If the rep provides a voice-note transcript, call summarize_voice_note
  (it will handle the consent check itself).
- After acting, reply in ONE short, friendly sentence confirming what you did.
  Never fabricate field values you weren't given evidence for.""")


def build_graph():
    llm = get_llm().bind_tools(ALL_TOOLS)

    def agent_node(state: AgentState):
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SYSTEM_PROMPT] + messages
        response = llm.invoke(messages)
        return {"messages": [response]}

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(ALL_TOOLS))

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()


# Compiled once at import time and reused across requests.
AGENT_GRAPH = build_graph()
