# --- START OF FILE main.py ---
import uvicorn
import tomli
import json
import re
import os
from starlette.responses import JSONResponse 
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard
from a2a.utils import new_agent_text_message, get_text_parts

from my_a2a import send_message
from green_agentv2 import grade_agent_performance, deconstruct_task_to_key_points

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
        print("🟢 WebJudge: Received assessment request.")
        user_input = context.get_user_input()
        inputs = parse_tags(user_input)
        
        white_agent_url = inputs.get("white_agent_url")
        task_prompt = inputs.get("task_prompt", "Default task")
        action_budget = int(inputs.get("action_budget", 10))

        if not white_agent_url:
            await event_queue.enqueue_event(new_agent_text_message("❌ Error: No <white_agent_url> provided."))
            return

        await event_queue.enqueue_event(new_agent_text_message(f"📋 Orchestrating Task: {task_prompt}"))

        try:
            print(f"👉 Sending task to White Agent at {white_agent_url}...")
            response_obj = await send_message(white_agent_url, task_prompt)
            
            res_result = response_obj.root.result
            text_parts = get_text_parts(res_result.parts)
            white_agent_response_text = text_parts[0] if text_parts else ""
            
            try:
                evidence_data = json.loads(white_agent_response_text)
                if "evidence_bundle" in evidence_data:
                    evidence_bundle = evidence_data["evidence_bundle"]
                else:
                    evidence_bundle = evidence_data

                screenshots = evidence_bundle.get("screenshots", [])
                action_trace = evidence_bundle.get("action_trace", "")
            except json.JSONDecodeError:
                await event_queue.enqueue_event(new_agent_text_message("❌ Error: White Agent response was not valid JSON."))
                return

            await event_queue.enqueue_event(new_agent_text_message("🧠 Grading evidence with Gemini..."))
            
            key_points = deconstruct_task_to_key_points(task_prompt)
            actions_taken = len(action_trace.split('\n')) if action_trace else 0
            
            evaluation = grade_agent_performance(
                key_points, screenshots, action_trace, actions_taken, action_budget
            )
            
            report = f"""
## 🏁 Evaluation Complete
**Verdict:** {evaluation.get("final_verdict", "UNKNOWN")}
**Score:** {evaluation.get("total_score", 0)}/100
**Reasoning:** {evaluation.get("summary_reasoning", "No summary")}

<json>
{json.dumps(evaluation, indent=2)}
</json>
            """
            await event_queue.enqueue_event(new_agent_text_message(report))

        except Exception as e:
            print(f"❌ Error during execution: {e}")
            await event_queue.enqueue_event(new_agent_text_message(f"❌ Error: {str(e)}"))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass


try:
    with open("agent_card.toml", "rb") as f:
        agent_card_dict = tomli.load(f)
except FileNotFoundError:
    print("⚠️ agent_card.toml not found!")
    agent_card_dict = {}

if os.environ.get("RENDER_EXTERNAL_URL"):
    agent_card_dict["url"] = os.environ.get("RENDER_EXTERNAL_URL")
else:
    agent_card_dict["url"] = "http://localhost:9001"

request_handler = DefaultRequestHandler(
    agent_executor=WebJudgeExecutor(),
    task_store=InMemoryTaskStore(),
)

a2a_app = A2AStarletteApplication(
    agent_card=AgentCard(**agent_card_dict),
    http_handler=request_handler,
)

app = a2a_app.build()

async def get_card(request):
    return JSONResponse(agent_card_dict)

async def get_status(request):
    return JSONResponse({"status": "ok", "agent": agent_card_dict.get("name")})

app.add_route("/", get_card, methods=["GET"])
app.add_route("/health", get_card, methods=["GET"]) 
app.add_route("/status", get_status, methods=["GET"])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 9001))
    uvicorn.run(app, host="0.0.0.0", port=port)

