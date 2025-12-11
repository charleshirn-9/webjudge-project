import uvicorn
import tomli
import json
import os
import base64
import asyncio
from starlette.responses import JSONResponse, Response
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard
from a2a.utils import new_agent_text_message

AGENT_URL = "https://unannoyed-alda-emigrational.ngrok-free.dev"

def screenshot_to_base64(screenshot_bytes):
    return base64.b64encode(screenshot_bytes).decode('utf-8')

class PlaywrightExecutor(AgentExecutor):    
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_prompt = context.get_user_input()
        print(f"\n🤖 White Agent: Received task -> '{task_prompt}'")
        print("🚀 Starting autonomous navigation...")
        await event_queue.enqueue_event(new_agent_text_message(f"Task received: {task_prompt}. Launching Browser..."))

        action_log = []
        screenshots_b64 = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=1000)
            page = await browser.new_page()

            try:
                print("   Step 1: Navigating to Search Engine...")
                await page.goto("https://duckduckgo.com")
                action_log.append("1. Navigated to https://duckduckgo.com")
                
                sc = await page.screenshot()
                screenshots_b64.append(screenshot_to_base64(sc))
                print(f"   Step 2: Searching for '{task_prompt}'...")
                await page.fill("input[name='q']", task_prompt)
                await page.press("input[name='q']", "Enter")
                action_log.append(f"2. Searched for: '{task_prompt}'")
                
                await page.wait_for_load_state("networkidle")
                
                sc = await page.screenshot()
                screenshots_b64.append(screenshot_to_base64(sc))

                print("   Step 3: Clicking first result...")
                try:
                    async with page.expect_navigation(timeout=15000):
                        await page.click("a[data-testid='result-title-a'] >> nth=0")
                    
                    current_url = page.url
                    print(f"   📍 Landed on: {current_url}")
                    action_log.append(f"3. Clicked first result. URL: {current_url}")
                    
                except Exception as e:
                    print(f"   ⚠️ Could not click result: {e}")
                    action_log.append("3. Failed to click on the first result (Time out or Selector changed).")

                print("   Step 4: Capturing final evidence...")
                await page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(1) 
                sc = await page.screenshot()
                screenshots_b64.append(screenshot_to_base64(sc))
                
            except Exception as e:
                print(f"❌ Critical Error during navigation: {e}")
                action_log.append(f"CRITICAL ERROR: {str(e)}")
            finally:
                await browser.close()

        print("📦 Packaging evidence...")
        response_payload = {
            "final_answer": f"Executed search for {task_prompt}",
            "evidence_bundle": {
                "screenshots": screenshots_b64,
                "action_trace": "\n".join(action_log)
            }
        }
        
        print("📤 Sending response back to Green Agent.")
        await event_queue.enqueue_event(new_agent_text_message(json.dumps(response_payload)))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass


card_data = {
    "name": "white-agent-playwright",
    "description": "Real Playwright White Agent",
    "version": "0.1.0",
    "defaultInputModes": ["text"],
    "defaultOutputModes": ["text"],
    "capabilities": {"streaming": False},
    "skills": [],
    "url": AGENT_URL
}

a2a_app = A2AStarletteApplication(
    agent_card=AgentCard(**card_data),
    http_handler=DefaultRequestHandler(
        agent_executor=PlaywrightExecutor(),
        task_store=InMemoryTaskStore()
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
    if request.method == "HEAD": return Response(media_type="application/json")
    return JSONResponse(card_data)

async def get_status(request):
    if request.method == "HEAD": return Response(media_type="application/json")
    return JSONResponse({"status": "ok"})

app.add_route("/", get_card, methods=["GET", "HEAD", "OPTIONS"])
app.add_route("/.well-known/agent-card.json", get_card, methods=["GET", "HEAD", "OPTIONS"])
app.add_route("/health", get_status, methods=["GET", "HEAD", "OPTIONS"])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
