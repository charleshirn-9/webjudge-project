import os
import tomli # Library to read the TOML file
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
from green_agent import evaluate_white_agent_output

app = FastAPI()

try:
    with open("webjudge.toml", "rb") as f:
        AGENT_CARD = tomli.load(f)
    if os.environ.get("RENDER_EXTERNAL_URL"):
        AGENT_CARD["url"] = os.environ.get("RENDER_EXTERNAL_URL")
except Exception as e:
    print(f"⚠️ Warning: Could not load webjudge.toml: {e}")
    AGENT_CARD = {"error": "Card not loaded"}

class EvidenceBundle(BaseModel):
    screenshots: List[str]
    action_trace: str

class AgentRequest(BaseModel):
    task_prompt: str
    action_budget: int
    evidence_bundle: EvidenceBundle


@app.get("/")
def get_agent_card():
    return AGENT_CARD

@app.get("/health")
def health_check():
    return {"status": "active", "model": "Gemini Green Agent"}

@app.post("/evaluate")
def run_evaluation(request: AgentRequest):
    print(f"📥 Received evaluation request for task: {request.task_prompt[:50]}...")
    
    payload = {
        "task_prompt": request.task_prompt,
        "action_budget": request.action_budget,
        "evidence_bundle": {
            "screenshots": request.evidence_bundle.screenshots,
            "action_trace": request.evidence_bundle.action_trace
        }
    }

    try:
        result = evaluate_white_agent_output(payload)
        return result
    except Exception as e:
        print(f"❌ Server Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
