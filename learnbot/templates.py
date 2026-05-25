from datetime import date
from langchain_core.prompts import ChatPromptTemplate


def get_course_query_template() -> ChatPromptTemplate:
    """
    Part A.1 — Academic advisor persona for course queries.
    Variables: platform_name, current_date, student_name, query
    """
    template = ChatPromptTemplate.from_messages([
        ("system", """You are an academic advisor for {platform_name}, an online learning platform.
Today's date is {current_date}.

Your responsibilities:
- Help students find the right courses based on their goals
- Explain prerequisites, modules, and course structure clearly
- Check enrollment status and provide progress updates
- Recommend learning paths based on student interests

Rules:
- Never complete assignments or provide exam answers
- Always encourage students to learn independently
- If a course is not in the catalog, say so honestly
- Keep responses concise and actionable"""),

        ("human", "Student: {student_name}\nQuestion: {query}"),
    ])
    return template


def get_support_ticket_template() -> ChatPromptTemplate:
    """
    Part A.2 — Help desk agent that creates structured support tickets.
    Variables: platform_name, current_date, issue_description
    Output format enforced: summary, priority, category, steps_taken
    """
    template = ChatPromptTemplate.from_messages([
        ("system", """You are a help desk agent for {platform_name}.
Today's date is {current_date}.

When a student reports an issue, create a structured support ticket in this EXACT format:

{{
  "summary": "<one sentence description of the issue>",
  "priority": "<LOW|MED|HIGH>",
  "category": "<account|payment|content|technical|other>",
  "steps_taken": ["<step 1>", "<step 2>"]
}}

Priority guidelines:
- HIGH: cannot access paid content, billing errors, account locked
- MED: slow loading, minor bugs, missing features
- LOW: general questions, feedback, suggestions

Always be empathetic and professional."""),

        ("human", "Issue: {issue_description}"),
    ])
    return template


def get_faq_template() -> ChatPromptTemplate:
    """
    Part A.3 — FAQ template with embedded few-shot examples in system prompt.
    Variables: platform_name, current_date, query
    """
    template = ChatPromptTemplate.from_messages([
        ("system", """You are a FAQ assistant for {platform_name}.
Today's date is {current_date}.

Answer common student questions quickly and accurately.

Examples:
Q: How do I reset my password?
A: Go to Settings > Security > Reset Password. Enter your registered email and check your inbox.

Q: Can I get a refund?
A: Refunds are available within 7 days of purchase. Go to My Courses > Purchase History > Request Refund.

Q: How do I download my certificate?
A: Complete 100% of the course. Then go to My Courses > Completed > Download Certificate.

Q: How do I change my email address?
A: Go to Settings > Profile > Edit Email. You will need to verify the new email address.

Q: Why can I not access my course?
A: Check your enrollment status under My Courses. If payment failed, go to Billing > Retry Payment.

Keep answers short, direct, and helpful. If the question is not FAQ-related, say so politely."""),

        ("human", "Question: {query}"),
    ])
    return template


def get_partial_templates(platform_name: str = "LearnSphere") -> dict:
    """
    Part A.4 — Apply .partial() to all three templates.
    Pre-fills platform_name and current_date so only dynamic vars needed at runtime.
    """
    today = str(date.today())

    course_template  = get_course_query_template().partial(
        platform_name=platform_name,
        current_date=today,
    )
    support_template = get_support_ticket_template().partial(
        platform_name=platform_name,
        current_date=today,
    )
    faq_template     = get_faq_template().partial(
        platform_name=platform_name,
        current_date=today,
    )

    return {
        "course":  course_template,
        "support": support_template,
        "faq":     faq_template,
    }