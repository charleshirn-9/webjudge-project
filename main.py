import uvicorn
import tomli
import json
import re
import os
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
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
        print("🟢 WebJudge: Starting Orchestration...")
        
        user_input = context.get_user_input()
        inputs = parse_tags(user_input)
        
        white_agent_url = inputs.get("white_agent_url")
        task_prompt = inputs.get("task_prompt", "Default task")
        action_budget = int(inputs.get("action_budget", 10))

        if not white_agent_url:
            await event_queue.enqueue_event(new_agent_text_message("❌ Error: No <white_agent_url> provided. I cannot contact the agent."))
            return

        await event_queue.enqueue_event(new_agent_text_message(f"📡 Contacting White Agent at: {white_agent_url}"))
        await event_queue.enqueue_event(new_agent_text_message(f"📋 Task sent: {task_prompt}"))

        try:
            response_obj = await send_message(white_agent_url, task_prompt)
            res_result = response_obj.root.result
            text_parts = get_text_parts(res_result.parts)
            white_agent_response_text = text_parts[0] if text_parts else ""
            
            print(f"📥 Received response from White Agent ({len(white_agent_response_text)} chars)")

            try:
                data = json.loads(white_agent_response_text)
                if "evidence_bundle" in data:
                    evidence = data["evidence_bundle"]
                else:
                    evidence = data 
                screenshots = evidence.get("screenshots", [])
                action_trace = evidence.get("action_trace", "")

                if not screenshots:
                    await event_queue.enqueue_event(new_agent_text_message("⚠️ Warning: White Agent returned no screenshots."))

            except json.JSONDecodeError:
                await event_queue.enqueue_event(new_agent_text_message("⚠️ Warning: White Agent response was not JSON. Treating entire response as action trace."))
                screenshots = []
                action_trace = white_agent_response_text

            await event_queue.enqueue_event(new_agent_text_message("🧠 Analyzing evidence with Gemini..."))
            
            key_points = deconstruct_task_to_key_points(task_prompt)
            actions_taken = len(action_trace.split('\n')) if action_trace else 0
            
            evaluation = grade_agent_performance(
                key_points, screenshots, action_trace, actions_taken, action_budget
            )
            
            verdict = evaluation.get("final_verdict", "UNKNOWN")
            score = evaluation.get("total_score", 0)
            reasoning = evaluation.get("summary_reasoning", "No summary provided.")
            
            final_report = f"""
## 🏁 Assessment Report

**Verdict:** {verdict}
**Score:** {score}/100

**Details:**
{reasoning}

<json>
{json.dumps(evaluation, indent=2)}
</json>
            """
            await event_queue.enqueue_event(new_agent_text_message(final_report))

        except Exception as e:
            error_msg = f"❌ Error during orchestration: {str(e)}"
            print(error_msg)
            await event_queue.enqueue_event(new_agent_text_message(error_msg))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass


try:
    with open("agent-card.toml", "rb") as f:
        agent_card_data = tomli.load(f)
except Exception:
    agent_card_data = {}

agent_card_data["url"] = RENDER_URL
AGENT_CARD_JSON = json.dumps(agent_card_data)

# A2A App
request_handler = DefaultRequestHandler(
    agent_executor=WebJudgeExecutor(),
    task_store=InMemoryTaskStore(),
)
a2a_app = A2AStarletteApplication(
    agent_card=AgentCard(**agent_card_data),
    http_handler=request_handler,
).build()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
@app.head("/")
async def root():
    return Response(content=AGENT_CARD_JSON, media_type="application/json")

@app.get("/.well-known/agent-card.json")
@app.head("/.well-known/agent-card.json")
async def well_known():
    return Response(content=AGENT_CARD_JSON, media_type="application/json")

@app.get("/health")
@app.head("/health")
@app.get("/status")
@app.head("/status")
async def health():
    return Response(content=json.dumps({"status": "ok"}), media_type="application/json")

@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
async def catch_all(request, path_name):
    return await a2a_app(request.scope, request.receive, request.send)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 9001))
    uvicorn.run(app, host="0.0.0.0", port=port)
