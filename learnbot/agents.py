from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from typing import Optional
import os

from .tools import get_course_info, check_enrollment_status, create_support_ticket, get_faq_answer


def get_llm(model: str = "gemini-2.5-flash") -> ChatGoogleGenerativeAI:
    """Initialize and return the LLM client with fallback options if needed."""
    return ChatGoogleGenerativeAI(
        model=model,  # Ensure your environment supports gemini-2.5-flash
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.2,
    )


def _make_agent(tools: list, system_prompt: str, llm) -> AgentExecutor:
    """
    Helper to build a ReAct AgentExecutor with given tools and system prompt.
    """
    tool_names   = ", ".join([t.name for t in tools])
    tool_strings = "\n".join([f"{t.name}: {t.description}" for t in tools])

    prompt = PromptTemplate.from_template(
        system_prompt + """

Tools available:
{tools}

Tool names: {tool_names}

Use this format:
Question: the input question
Thought: what to do
Action: tool name from [{tool_names}]
Action Input: input to the tool
Observation: tool result
... (repeat as needed)
Thought: I have the answer
Final Answer: the answer

Question: {input}
Thought: {agent_scratchpad}"""
    )

    agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        max_iterations=5,
        handle_parsing_errors=True,
        verbose=False,
    )


def get_course_agent(llm=None) -> AgentExecutor:
    """
    Part C.2 — Course agent scoped to course info and enrollment tools only.
    """
    if llm is None:
        llm = get_llm()

    system_prompt = """You are an academic advisor for LearnSphere.
You help students with course information, prerequisites, modules, and enrollment status.
Only use the tools provided. Do not answer questions outside course and enrollment topics.
Always be encouraging and guide students toward their learning goals."""

    return _make_agent(
        tools=[get_course_info, check_enrollment_status],
        system_prompt=system_prompt,
        llm=llm,
    )


def get_support_agent(llm=None) -> AgentExecutor:
    """
    Part C.3 — Support agent scoped to ticket creation and FAQ lookup only.
    """
    if llm is None:
        llm = get_llm()

    system_prompt = """You are a help desk agent for LearnSphere.
You create support tickets for student issues and look up FAQ answers.
Only use the tools provided. Do not answer questions about course content or enrollment.
Always be empathetic, professional, and action-oriented."""

    return _make_agent(
        tools=[create_support_ticket, get_faq_answer],
        system_prompt=system_prompt,
        llm=llm,
    )


def get_faq_agent(llm=None) -> AgentExecutor:
    """
    Part C.4 — FAQ agent scoped to FAQ lookup only. Optimized for quick answers.
    """
    if llm is None:
        llm = get_llm()

    system_prompt = """You are a quick-answer FAQ bot for LearnSphere.
You look up answers to common student questions using the FAQ tool.
Keep answers short, direct, and helpful.
Do not answer questions outside what the FAQ tool covers."""

    return _make_agent(
        tools=[get_faq_answer],
        system_prompt=system_prompt,
        llm=llm,
    )
