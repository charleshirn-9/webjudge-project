import uvicorn
import tomli
import json
import re
import os

from starlette.responses import JSONResponse, Response
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard
from a2a.utils import new_agent_text_message, get_text_parts

from my_a2a import send_message
from green_agentv2 import grade_agent_performance, deconstruct_task_to_key_points

RENDER_URL = "https://webjudge-project.onrender.com"

def parse_tags(text):
    tags = {}
    for tag in ["white_agent_url", "task_prompt", "action_budget"]:
        pattern = f"<{tag}>(.*?)</{tag}>"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            tags[tag] = match.group(1).strip()
    return tags

class WebJudgeExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        print("🟢 WebJudge: Orchestration Start.")
        
        execution_log = []
        
        user_input = context.get_user_input()
        inputs = parse_tags(user_input)
        
        white_agent_url = inputs.get("white_agent_url")
        task_prompt = inputs.get("task_prompt", "Default task")
        action_budget = int(inputs.get("action_budget", 10))

        if not white_agent_url:
            await event_queue.enqueue_event(new_agent_text_message("❌ Error: No <white_agent_url>."))
            return

        execution_log.append(f"📡 Orchestrating Task: {task_prompt}")
        execution_log.append(f"👉 Target Agent: {white_agent_url}\n")

        try:
            response_obj = await send_message(white_agent_url, task_prompt)
            res_result = response_obj.root.result
            text_parts = get_text_parts(res_result.parts)
            white_resp = text_parts[0] if text_parts else ""
            
            try:
                data = json.loads(white_resp)
                evidence = data.get("evidence_bundle", data)
                screenshots = evidence.get("screenshots", [])
                action_trace = evidence.get("action_trace", "")
                execution_log.append(f"✅ Received Evidence ({len(screenshots)} screenshots).")
            except json.JSONDecodeError:
                screenshots = []
                action_trace = white_resp
                execution_log.append("⚠️ Warning: Received raw text evidence.")

            execution_log.append("🧠 Grading with Gemini...")
            key_points = deconstruct_task_to_key_points(task_prompt)
            actions_taken = len(action_trace.split('\n')) if action_trace else 0
            
            eval_res = grade_agent_performance(
                key_points, screenshots, action_trace, actions_taken, action_budget
            )
            
            report = f"""
## 🏁 Verdict: {eval_res.get("final_verdict", "UNKNOWN")}
**Score:** {eval_res.get("total_score", 0)}/100
**Reasoning:** {eval_res.get("summary_reasoning", "N/A")}

### Details
{eval_res.get("rubric_scores", {})}
            """
            execution_log.append(report)
            
            # --- ENVOI FINAL UNIQUE ---
            # On joint tout le texte et on l'envoie en une seule fois
            full_response = "\n".join(execution_log)
            await event_queue.enqueue_event(new_agent_text_message(full_response))

        except Exception as e:
            print(f"❌ Error: {e}")
            await event_queue.enqueue_event(new_agent_text_message(f"Error during execution: {e}"))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass

try:
    with open("agent-card.toml", "rb") as f:
        card_data = tomli.load(f)
except Exception:
    card_data = {}

card_data["url"] = RENDER_URL
AGENT_CARD_JSON = json.dumps(card_data)

a2a_app = A2AStarletteApplication(
    agent_card=AgentCard(**card_data),
    http_handler=DefaultRequestHandler(
        agent_executor=WebJudgeExecutor(),
        task_store=InMemoryTaskStore(),
    ),
)

app = a2a_app.build()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_card(request):
    if request.method == "HEAD":
        return Response(media_type="application/json")
    return JSONResponse(card_data)

async def get_status(request):
    if request.method == "HEAD":
        return Response(media_type="application/json")
    return JSONResponse({"status": "ok", "agent": card_data.get("name")})

app.add_route("/", get_card, methods=["GET", "HEAD", "OPTIONS"])
app.add_route("/.well-known/agent-card.json", get_card, methods=["GET", "HEAD", "OPTIONS"])
app.add_route("/health", get_status, methods=["GET", "HEAD", "OPTIONS"])
app.add_route("/status", get_status, methods=["GET", "HEAD", "OPTIONS"])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 9001))
    uvicorn.run(app, host="0.0.0.0", port=port)
