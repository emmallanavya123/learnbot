import os
from dotenv import load_dotenv

load_dotenv()
from flask import Flask, render_template, request, jsonify
from learnbot.database import init_db
from learnbot.graph import learnbot_graph
from learnbot.models import LearnBotState

app = Flask(__name__)

conversation_history = []

init_db()


def format_response(text: str) -> str:
    """Convert newlines to <br> for HTML display."""
    if not text:
        return ""
    text = text.replace('\n\n', '<br><br>')
    text = text.replace('\n', '<br>')
    return text.strip()


@app.route('/', methods=['GET', 'POST'])
def index():
    status        = None
    response      = None
    intent        = None
    agent_used    = None
    safety_flags  = []
    tool_calls    = []

    if request.method == 'POST':
        user_input = request.form.get('user_input', '').strip()

        if user_input:
            # Build initial state
            initial_state: LearnBotState = {
                "messages":            [],
                "user_input":          user_input,
                "intent":              None,
                "safety_status":       "safe",
                "safety_flags":        [],
                "agent_response":      None,
                "tool_calls_made":     [],
                "processing_metadata": {},
            }

            try:
                result     = learnbot_graph.invoke(initial_state)
                status     = result["safety_status"].upper()
                response   = format_response(result.get("agent_response", ""))
                intent     = result.get("intent")
                agent_used = result["processing_metadata"].get("agent_used")
                tool_calls = result.get("tool_calls_made", [])
                safety_flags = result.get("safety_flags", [])

                conversation_history.append({
                    "user":  user_input,
                    "bot":   response,
                    "intent": intent,
                })

            except Exception as e:
                status   = "ERROR"
                response = f"Something went wrong: {e}"

    return render_template(
        'index.html',
        status=status,
        response=response,
        intent=intent,
        agent_used=agent_used,
        tool_calls=tool_calls,
        safety_flags=safety_flags,
        history=conversation_history,
    )


@app.route('/health')
def health():
    return jsonify({"status": "ok", "service": "LearnBot"})


if __name__ == '__main__':
    app.run(debug=True, port=5000)