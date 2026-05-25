from enum import Enum
from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage


class QueryType(str, Enum):
    course_query  = "course"
    support       = "support"
    faq           = "faq"
    other         = "other"


class SafetyStatus(str, Enum):
    safe          = "safe"
    unsafe        = "unsafe"
    review_needed = "review_needed"


class LearnBotState(TypedDict):
    messages:            List[BaseMessage]   # full conversation history
    user_input:          str                 # current raw user message
    intent:              Optional[str]       # course / support / faq
    safety_status:       str                 # safe | unsafe | review_needed
    safety_flags:        List[Dict]          # detected patterns with severity
    agent_response:      Optional[str]       # final response from routed agent
    tool_calls_made:     List[str]           # ordered list of tool names invoked
    processing_metadata: Dict[str, Any]      # timestamps, token counts, agent_used