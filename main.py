from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from green_agentv2 import evaluate_white_agent_output

app = FastAPI()

class EvidenceBundle(BaseModel):
    screenshots: List[str] 
    action_trace: str

class AgentRequest(BaseModel):
    task_prompt: str
    action_budget: int
    evidence_bundle: EvidenceBundle

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