from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
import base64
import time
import uvicorn

app = FastAPI()

# 1. Modèle de données : Ce que AgentBeats envoie au White Agent
class TaskRequest(BaseModel):
    task_prompt: str
    action_budget: int = 10 # Valeur par défaut si non fournie

# Fonction utilitaire pour les images
def screenshot_to_base64(screenshot_bytes):
    return base64.b64encode(screenshot_bytes).decode('utf-8')

@app.get("/health")
def health_check():
    return {"status": "active", "type": "White Agent Naive"}

# 2. Le Endpoint principal : AgentBeats appelle ceci pour lancer la tâche
@app.post("/solve")
def solve_task(request: TaskRequest):
    print(f"📥 Received task: {request.task_prompt}")
    
    action_log = []
    screenshots_b64 = []

    # On lance Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) 
        page = browser.new_page()

        try:
            # --- Étape 1 : DuckDuckGo ---
            page.goto("https://duckduckgo.com")
            action_log.append("1. Navigated to https://duckduckgo.com")
            screenshots_b64.append(screenshot_to_base64(page.screenshot()))

            # --- Étape 2 : Recherche ---
            page.fill("input[name='q']", request.task_prompt)
            page.press("input[name='q']", "Enter")
            action_log.append(f"2. Searched for: '{request.task_prompt}'")
            page.wait_for_load_state("networkidle")
            screenshots_b64.append(screenshot_to_base64(page.screenshot()))

            # --- Étape 3 : Clic (Tentative) ---
            try:
                with page.expect_navigation(timeout=10000):
                    page.click("a[data-testid='result-title-a'] >> nth=0")
                
                current_url = page.url
                action_log.append(f"3. Clicked first result. URL: {current_url}")
            except Exception:
                action_log.append("3. Failed to click first result (timeout or not found).")

            # Capture finale
            time.sleep(2)
            screenshots_b64.append(screenshot_to_base64(page.screenshot()))
            
        except Exception as e:
            print(f"⚠️ Error during execution: {e}")
            action_log.append(f"CRITICAL ERROR: {str(e)}")
        finally:
            browser.close()

    print("✅ Task finished. Returning evidence.")

    # 3. Réponse : On renvoie exactement ce que le Green Agent attend
    return {
        "final_answer": {
            "summary": "Task attempted via DuckDuckGo search."
        },
        "evidence_bundle": {
            "screenshots": screenshots_b64,
            "action_trace": "\n".join(action_log)
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)