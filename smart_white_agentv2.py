import uvicorn
import tomli
import json
import os
import base64
import asyncio
import google.generativeai as genai
from PIL import Image
import io

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

try:
    genai.configure(api_key="AIzaSyAJbwTQmNHbzaiHU3Dzn_MUoIeV52v9DZ8")
except KeyError:
    print("❌ ERREUR: GOOGLE_API_KEY manquante.")

model = genai.GenerativeModel('gemini-flash-latest')

def screenshot_to_base64(screenshot_bytes):
    return base64.b64encode(screenshot_bytes).decode('utf-8')

def bytes_to_image(screenshot_bytes):
    return Image.open(io.BytesIO(screenshot_bytes))

class SmartPlaywrightExecutor(AgentExecutor):
    
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        raw_task = context.get_user_input()
        print(f"\n🧠 Smart Agent: Received raw task -> '{raw_task}'")
        await event_queue.enqueue_event(new_agent_text_message(f"Analyzing task: {raw_task}..."))

        print("   ✨ Optimizing search query...")
        optimization_prompt = f"""
        You are a search engine expert.
        User Task: "{raw_task}"
        
        Extract the best, concise keyword search query to find the item or solve the task.
        Remove unnecessary words like "find", "look for", "show me".
        Keep specific details like model names, colors, prices if mentioned.
        
        Output ONLY the query string. No quotes, no markdown.
        """
        try:
            resp = model.generate_content(optimization_prompt)
            search_query = resp.text.strip()
            print(f"   🔍 Optimized Query: '{search_query}'")
            await event_queue.enqueue_event(new_agent_text_message(f"Optimized search query: '{search_query}'"))
        except Exception as e:
            print(f"   ⚠️ Optimization failed, using raw task. Error: {e}")
            search_query = raw_task

        action_log = []
        screenshots_b64 = []
        MAX_STEPS = 10 

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=200)
            context = await browser.new_context(viewport={"width": 1280, "height": 720})
            page = await context.new_page()

            try:
                # 2. Démarrage
                await page.goto("https://duckduckgo.com")
                print("   📍 Start: DuckDuckGo")
                
                for step in range(MAX_STEPS):
                    print(f"\n--- Step {step + 1}/{MAX_STEPS} ---")
                    await asyncio.sleep(1)
                    screenshot_bytes = await page.screenshot()
                    img_pil = bytes_to_image(screenshot_bytes)
                    screenshots_b64.append(screenshot_to_base64(screenshot_bytes))

                    prompt = f"""
                    You are an autonomous web agent. 
                    User Goal: "{raw_task}"
                    Your Prepared Search Query: "{search_query}"
                    
                    Analyze the screenshot. Decide the next action.
                    
                    Tools (Respond in JSON):
                    1. {{ "action": "type", "text": "{search_query}" }} -> Type the prepared query into a search box.
                    2. {{ "action": "click", "text": "visual text" }} -> Click an element (link, button).
                    3. {{ "action": "scroll" }} -> Scroll down.
                    4. {{ "action": "done" }} -> Goal achieved.
                    
                    Choose the best action. JSON ONLY.
                    """
                    
                    try:
                        response = model.generate_content([prompt, img_pil])
                        text_resp = response.text.replace("```json", "").replace("```", "").strip()
                        decision = json.loads(text_resp)
                        print(f"   🤖 Thought: {decision}")
                    except Exception as e:
                        print(f"   ⚠️ Brain Error: {e}")
                        action_log.append(f"Brain Error: {e}")
                        break

                    action_type = decision.get("action")
                    action_log.append(f"Step {step+1}: {decision}")

                    # 4. Exécution
                    if action_type == "type":
                        text_to_type = decision.get("text", search_query) 
                        print(f"   ⌨️ Typing: {text_to_type}")
                        try:
                            await page.get_by_role("searchbox").fill(text_to_type)
                            await page.keyboard.press("Enter")
                        except:
                            await page.keyboard.type(text_to_type)
                            await page.keyboard.press("Enter")
                        await page.wait_for_load_state("networkidle")

                    elif action_type == "click":
                        target_text = decision.get("text")
                        print(f"   🖱️ Clicking: {target_text}")
                        try:
                            await page.get_by_text(target_text, exact=False).first.click(timeout=5000)
                            await page.wait_for_load_state("domcontentloaded")
                        except Exception as e:
                            print(f"   ❌ Click Failed: {e}")

                    elif action_type == "scroll":
                        print("   📜 Scrolling...")
                        await page.mouse.wheel(0, 500)
                        await asyncio.sleep(1)

                    elif action_type == "done":
                        print("   🎉 Task Completed.")
                        break
                    
                    else:
                        print("   ❓ Unknown action, skipping.")

            except Exception as e:
                print(f"❌ Critical Error: {e}")
                action_log.append(f"CRITICAL ERROR: {str(e)}")
            finally:
                await browser.close()

        # 5. Envoi des preuves
        response_payload = {
            "final_answer": f"Executed: {search_query}",
            "evidence_bundle": {
                "screenshots": screenshots_b64,
                "action_trace": "\n".join(action_log)
            }
        }
        
        await event_queue.enqueue_event(new_agent_text_message(json.dumps(response_payload)))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass


card_data = {
    "name": "smart-white-agent",
    "description": "Smart Multimodal Agent",
    "version": "1.1.0",
    "defaultInputModes": ["text"],
    "defaultOutputModes": ["text"],
    "capabilities": {"streaming": False},
    "skills": [],
    "url": AGENT_URL
}

a2a_app = A2AStarletteApplication(
    agent_card=AgentCard(**card_data),
    http_handler=DefaultRequestHandler(
        agent_executor=SmartPlaywrightExecutor(),
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
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
    