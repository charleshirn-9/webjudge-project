# --- START OF FILE main.py ---
import uvicorn
import tomli
import json
import os
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard

# Tes imports
from green_agentv2 import grade_agent_performance, deconstruct_task_to_key_points

RENDER_URL = "https://webjudge-project.onrender.com"

try:
    with open("agent_card.toml", "rb") as f:
        agent_card_data = tomli.load(f)
except Exception as e:
    print(f"⚠️ Error loading TOML: {e}")
    agent_card_data = {"error": "toml_load_failed"}

agent_card_data["url"] = RENDER_URL
AGENT_CARD_JSON = json.dumps(agent_card_data)

class WebJudgeExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass 
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass

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
