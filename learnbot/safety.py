import re
import time
from typing import Dict, List, Tuple


# Threat patterns mapped to severity
THREAT_PATTERNS = {
    "homework_fraud": {
        "severity": "CRITICAL",
        "patterns": [
            r"\bwrite\s+my\s+(essay|assignment|report|thesis)\b",
            r"\bsolve\s+this\s+(assignment|problem|homework|quiz)\b",
            r"\bcomplete\s+my\s+(quiz|assignment|exam|homework)\b",
            r"\bdo\s+my\s+homework\b",
            r"\bfinish\s+my\s+assignment\b",
        ],
    },
    "academic_dishonesty": {
        "severity": "CRITICAL",
        "patterns": [
            r"\bcheat\b",
            r"\bplagiari[sz]e\b",
            r"\bcopy\s+answer\b",
            r"\bexam\s+answers?\b",
            r"\bpast\s+paper\s+answers?\b",
        ],
    },
    "data_exfiltration": {
        "severity": "HIGH",
        "patterns": [
            r"\blist\s+all\s+students\b",
            r"\bexport\s+grades?\b",
            r"\bshow\s+(the\s+)?database\b",
            r"\bdump\s+student\s+data\b",
            r"\bget\s+all\s+emails?\b",
        ],
    },
    "prompt_manipulation": {
        "severity": "HIGH",
        "patterns": [
            r"\bignore\s+(previous|prior|above)\s+instructions?\b",
            r"\bact\s+as\b",
            r"\bjailbreak\b",
            r"\bpretend\s+(you\s+are|to\s+be)\b",
            r"\bforget\s+your\s+instructions?\b",
            r"\boverride\s+(your\s+)?(rules?|instructions?|guidelines?)\b",
        ],
    },
    "scope_creep": {
        "severity": "LOW",
        "patterns": [
            r"\bwrite\s+me\s+a\s+(poem|story|song|joke)\b",
            r"\bplay\s+a\s+game\b",
            r"\btell\s+me\s+about\s+(politics|sports|movies)\b",
        ],
    },
}


def education_injection_detector(text: str) -> Dict:
    """
    Detect education-specific safety threats in user input.
    Returns structured result with flagged status, category, severity, message.
    CRITICAL severity halts processing immediately.
    """
    normalized = text.lower().strip()
    flags: List[Dict] = []

    for category, config in THREAT_PATTERNS.items():
        for pattern in config["patterns"]:
            if re.search(pattern, normalized, re.IGNORECASE):
                flags.append({
                    "flagged":   True,
                    "category":  category,
                    "severity":  config["severity"],
                    "message":   f"Detected {category.replace('_', ' ')} pattern: '{pattern}'",
                })
                break  # one flag per category is enough

    if not flags:
        return {
            "flagged":       False,
            "category":      None,
            "severity":      None,
            "message":       "Input is safe",
            "all_flags":     [],
            "safety_status": "safe",
        }

    # If any CRITICAL flag found — halt immediately
    critical = [f for f in flags if f["severity"] == "CRITICAL"]
    safety_status = "unsafe" if critical else "review_needed"

    return {
        "flagged":       True,
        "category":      flags[0]["category"],
        "severity":      flags[0]["severity"],
        "message":       flags[0]["message"],
        "all_flags":     flags,
        "safety_status": safety_status,
    }


def output_content_filter(response: str) -> Dict:
    """
    Filter LLM output to ensure it doesn't contain policy violations.
    Returns structured result with is_safe flag and list of issues.
    """
    issues: List[str] = []
    normalized = response.lower()

    # Check for direct homework answers
    homework_patterns = [
        r"\bhere\s+is\s+your\s+(essay|assignment|answer)\b",
        r"\bthe\s+answer\s+to\s+your\s+(quiz|exam|assignment)\s+is\b",
    ]
    for pattern in homework_patterns:
        if re.search(pattern, normalized):
            issues.append("Response contains direct homework answer")

    # Check for student data exposure
    data_patterns = [
        r"\bstudent\s+id\s*:\s*\d+\b",
        r"\bemail\s*:\s*\S+@\S+\b",
        r"\bgrade\s*:\s*[A-F]\d*\b",
    ]
    for pattern in data_patterns:
        if re.search(pattern, normalized):
            issues.append("Response may expose student data")

    # Check for leaked system prompt
    if any(phrase in normalized for phrase in [
        "system prompt", "my instructions", "i was told to",
        "my rules are", "prohibited behaviors"
    ]):
        issues.append("Response may contain leaked system instructions")

    return {
        "is_safe": len(issues) == 0,
        "issues":  issues,
    }


def safe_learnsphere_invoke(user_input: str, template, llm) -> Dict:
    """
    Full safe invocation pipeline:
    injection_detector → LLM invocation → output_filter
    Returns {status, response, flags, processing_time_ms}
    """
    start_time = time.time()

    # Step 1 — Safety check
    detection = education_injection_detector(user_input)

    if detection["flagged"]:
        return {
            "status":              "BLOCKED",
            "response":            "Your request could not be processed due to a policy violation.",
            "flags":               detection["all_flags"],
            "processing_time_ms":  int((time.time() - start_time) * 1000),
        }

    # Step 2 — Invoke LLM
    try:
        chain    = template | llm
        response = chain.invoke({"query": user_input})
        raw_text = response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        return {
            "status":              "ERROR",
            "response":            f"LLM invocation failed: {e}",
            "flags":               [],
            "processing_time_ms":  int((time.time() - start_time) * 1000),
        }

    # Step 3 — Output filter
    filter_result = output_content_filter(raw_text)

    if not filter_result["is_safe"]:
        return {
            "status":              "BLOCKED",
            "response":            "The response was blocked due to output policy violations.",
            "flags":               [{"category": "output_violation", "issues": filter_result["issues"]}],
            "processing_time_ms":  int((time.time() - start_time) * 1000),
        }

    return {
        "status":              "SUCCESS",
        "response":            raw_text,
        "flags":               [],
        "processing_time_ms":  int((time.time() - start_time) * 1000),
    }