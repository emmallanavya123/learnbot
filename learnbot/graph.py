import time
from typing import Any, Dict
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END

from .models import LearnBotState
from .safety import education_injection_detector
from .agents import get_llm, get_course_agent, get_support_agent, get_faq_agent

# REFLECTION 1:
# Why TypedDict over plain dict for state?
# TypedDict gives static type checking — mypy and IDEs catch mistakes at
# write-time instead of runtime. It also self-documents what fields the
# graph expects, making the codebase easier to maintain and extend.

# REFLECTION 2:
# Why conditional edges over a single router node?
# Conditional edges are declarative — LangGraph can visualize and compile
# them into a graph diagram. A single router node would hide the branching
# logic inside imperative code, making it harder to inspect, test, or
# swap individual branches without touching the router itself.

# REFLECTION 3:
# How to add memory/persistence across sessions?
# Use LangGraph's checkpointer (SqliteSaver or RedisSaver). Pass it to
# StateGraph.compile(checkpointer=...) and provide a thread_id per user
# session. The graph will automatically save and restore state between
# invocations so conversation history persists across page reloads.


# ── Node 1 — receive_input ──────────────────────────────────────────────────

def receive_input(state: LearnBotState) -> LearnBotState:
    """Parse user message, initialize state fields, log entry timestamp."""
    return {
        **state,
        "messages": state.get("messages", []) + [
            HumanMessage(content=state["user_input"])
        ],
        "intent":            None,
        "safety_status":     "safe",
        "safety_flags":      [],
        "agent_response":    None,
        "tool_calls_made":   [],
        "processing_metadata": {
            "entry_timestamp": time.time(),
            "agent_used":      None,
            "token_count":     0,
        },
    }


# ── Node 2 — safety_check ───────────────────────────────────────────────────

def safety_check(state: LearnBotState) -> LearnBotState:
    """Run education_injection_detector and populate safety_status + safety_flags."""
    detection = education_injection_detector(state["user_input"])

    return {
        **state,
        "safety_status": detection["safety_status"],
        "safety_flags":  detection.get("all_flags", []),
    }


def route_after_safety(state: LearnBotState) -> str:
    """
    Conditional edge after safety_check.
    safe → intent_classifier | unsafe/review_needed → rejection_handler
    """
    if state["safety_status"] == "safe":
        return "intent_classifier"
    return "rejection_handler"


# ── Node 3 — intent_classifier ──────────────────────────────────────────────

def intent_classifier(state: LearnBotState) -> LearnBotState:
    """
    Classify user intent using keyword matching.
    Sets intent field to: course | support | faq
    """

    text = state["user_input"].lower()

    # ── Support checked FIRST ─────────────────────────────────────────────
    # Must come before course keywords because
    # "cannot access my course videos" contains "course"
    # but the real intent is support
    support_keywords = [
        "cannot access", "can't access", "cant access",
        "unable to access", "not able to access",
        "video not", "videos not", "not loading",
        "not working", "doesn't work", "doesnt work",
        "won't load", "wont load", "won't play", "wont play",
        "error", "bug", "broken", "crash",
        "blank screen", "black screen", "stuck", "frozen",
        "refund", "billing", "payment", "charged",
        "invoice", "subscription",
        "locked out", "account locked",
        "cannot login", "can't login",
        "problem", "issue", "trouble",
        "not able to", "support", "ticket",
        "help me", "slow", "lagging",
    ]

    # ── Course checked SECOND ─────────────────────────────────────────────
    course_keywords = [
        "prerequisite", "prerequisites",
        "enroll", "enrollment", "enrolled",
        "curriculum", "syllabus",
        "module", "modules",
        "lesson", "lessons",
        "learning path", "roadmap",
        "which course", "what course",
        "course details", "course info",
        "course content", "course structure",
        "recommend a course", "suggest a course",
        "how long is the course",
        "certificate", "completion",
    ]

    # ── FAQ checked LAST ──────────────────────────────────────────────────
    faq_keywords = [
        "how do i", "how to", "how can i",
        "what is", "what are",
        "where can i", "where do i",
        "reset password", "change password",
        "update email", "change email",
        "download certificate",
        "account settings", "profile",
    ]

    # Priority: support → course → faq
    if any(kw in text for kw in support_keywords):
        intent = "support"
    elif any(kw in text for kw in course_keywords):
        intent = "course"
    elif any(kw in text for kw in faq_keywords):
        intent = "faq"
    else:
        intent = "faq"

    print(f"[INTENT] '{state['user_input']}' → {intent}")
    return {**state, "intent": intent}


def route_after_intent(state: LearnBotState) -> str:
    """
    Conditional edge after intent_classifier.
    course → course_handler | support → support_handler | faq → faq_handler
    """
    intent_map = {
        "course":  "course_handler",
        "support": "support_handler",
        "faq":     "faq_handler",
    }
    return intent_map.get(state["intent"], "faq_handler")


# ── Rejection handler ───────────────────────────────────────────────────────

def rejection_handler(state: LearnBotState) -> LearnBotState:
    """Return a safe refusal message for blocked inputs."""
    flag_summary = ""
    if state["safety_flags"]:
        categories = [f["category"] for f in state["safety_flags"]]
        flag_summary = f" (Detected: {', '.join(categories)})"

    response = (
        f"Your request could not be processed due to a policy violation{flag_summary}. "
        "Please rephrase your question and try again."
    )
    return {
        **state,
        "agent_response": response,
        "messages": state["messages"] + [AIMessage(content=response)],
        "processing_metadata": {
            **state["processing_metadata"],
            "agent_used":      "rejection_handler",
            "exit_timestamp":  time.time(),
        },
    }


# ── Node 4 — course_handler ─────────────────────────────────────────────────

def course_handler(state: LearnBotState) -> LearnBotState:
    """Invoke course_agent and extract response + tool calls."""
    try:
        agent  = get_course_agent()
        result = agent.invoke({"input": state["user_input"]})

        response       = result.get("output", "Sorry, I could not find course information.")
        tool_calls     = [step[0].tool for step in result.get("intermediate_steps", [])]

    except Exception as e:
        response   = f"Course lookup failed: {e}"
        tool_calls = []

    return {
        **state,
        "agent_response":  response,
        "tool_calls_made": tool_calls,
        "messages":        state["messages"] + [AIMessage(content=response)],
        "processing_metadata": {
            **state["processing_metadata"],
            "agent_used":     "course_agent",
            "exit_timestamp": time.time(),
        },
    }


# ── Node 5 — support_handler ────────────────────────────────────────────────

def support_handler(state: LearnBotState) -> LearnBotState:
    """Invoke support_agent and extract response + tool calls."""
    try:
        agent  = get_support_agent()
        result = agent.invoke({"input": state["user_input"]})

        response   = result.get("output", "Sorry, I could not process your support request.")
        tool_calls = [step[0].tool for step in result.get("intermediate_steps", [])]

    except Exception as e:
        response   = f"Support request failed: {e}"
        tool_calls = []

    return {
        **state,
        "agent_response":  response,
        "tool_calls_made": tool_calls,
        "messages":        state["messages"] + [AIMessage(content=response)],
        "processing_metadata": {
            **state["processing_metadata"],
            "agent_used":     "support_agent",
            "exit_timestamp": time.time(),
        },
    }


# ── Node 6 — faq_handler ────────────────────────────────────────────────────

def faq_handler(state: LearnBotState) -> LearnBotState:
    """Invoke faq_agent and extract response + tool calls."""
    try:
        agent  = get_faq_agent()
        result = agent.invoke({"input": state["user_input"]})

        response   = result.get("output", "Sorry, I could not find an FAQ answer.")
        tool_calls = [step[0].tool for step in result.get("intermediate_steps", [])]

    except Exception as e:
        response   = f"FAQ lookup failed: {e}"
        tool_calls = []

    return {
        **state,
        "agent_response":  response,
        "tool_calls_made": tool_calls,
        "messages":        state["messages"] + [AIMessage(content=response)],
        "processing_metadata": {
            **state["processing_metadata"],
            "agent_used":     "faq_agent",
            "exit_timestamp": time.time(),
        },
    }


# ── Build and compile the graph ─────────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Assemble the full LearnBot LangGraph workflow.
    """
    graph = StateGraph(LearnBotState)

    # Add all nodes
    graph.add_node("receive_input",    receive_input)
    graph.add_node("safety_check",     safety_check)
    graph.add_node("intent_classifier",intent_classifier)
    graph.add_node("rejection_handler",rejection_handler)
    graph.add_node("course_handler",   course_handler)
    graph.add_node("support_handler",  support_handler)
    graph.add_node("faq_handler",      faq_handler)

    # Entry point
    graph.set_entry_point("receive_input")

    # Unconditional edges
    graph.add_edge("receive_input", "safety_check")

    # Conditional edge 1 — after safety check
    graph.add_conditional_edges(
        "safety_check",
        route_after_safety,
        {
            "intent_classifier": "intent_classifier",
            "rejection_handler": "rejection_handler",
        }
    )

    # Conditional edge 2 — after intent classification
    graph.add_conditional_edges(
        "intent_classifier",
        route_after_intent,
        {
            "course_handler":  "course_handler",
            "support_handler": "support_handler",
            "faq_handler":     "faq_handler",
        }
    )

    # All handlers connect to END
    graph.add_edge("rejection_handler", END)
    graph.add_edge("course_handler",    END)
    graph.add_edge("support_handler",   END)
    graph.add_edge("faq_handler",       END)

    return graph.compile()


# Singleton compiled graph
learnbot_graph = build_graph()

learnbot_graph.get_graph().draw_mermaid_png(output_file_path="learnbot_graph.png")