import uvicorn
import json
import os
import base64
import asyncio
import google.generativeai as genai
from PIL import Image
import io
from playwright_stealth import Stealth


from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard
from a2a.utils import new_agent_text_message

from playwright.async_api import async_playwright
from starlette.responses import JSONResponse, Response
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware


AGENT_URL = "https://webjudge-white-agent.onrender.com"

try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
except KeyError:
    pass

model = genai.GenerativeModel('gemini-flash-latest')

def screenshot_to_base64(screenshot_bytes):
    return base64.b64encode(screenshot_bytes).decode('utf-8')

def bytes_to_image(screenshot_bytes):
    return Image.open(io.BytesIO(screenshot_bytes))

class SmartPlaywrightExecutor(AgentExecutor):
    
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        raw_task = context.get_user_input()
        print(f"\n🧠 Smart Agent: Received task -> '{raw_task}'")
        
        print("   ✨ Optimizing search query...")
        search_query = raw_task
        try:
            opt_prompt = f"Convert this task into a short search engine query: '{raw_task}'. Output ONLY the query."
            resp = model.generate_content(opt_prompt)
            search_query = resp.text.strip().replace('"', '')
            print(f"   🔍 Query: '{search_query}'")
        except:
            pass

        action_log = []
        screenshots_b64 = []
        MAX_STEPS = 8
        
        last_action_text = ""
        loop_count = 0

        async with Stealth().use_async(async_playwright()) as p:
            is_render = os.environ.get("RENDER") is not None
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage"
                ]
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()


            try:
                encoded_query = search_query.replace(" ", "+")
                start_url = f"https://duckduckgo.com/?q={encoded_query}&t=h_&ia=web"
                print(f"   📍 Navigating directly to: {start_url}")
                
                await page.goto(start_url)
                action_log.append(f"1. Direct navigation to search: {search_query}")
                
                await page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(3)

                for step in range(MAX_STEPS):
                    print(f"\n--- Step {step + 1}/{MAX_STEPS} ---")
                    
                    try:
                        screenshot_bytes = await page.screenshot(timeout=5000)
                        img_pil = bytes_to_image(screenshot_bytes)
                        screenshots_b64.append(screenshot_to_base64(screenshot_bytes))
                    except Exception as e:
                        print(f"Capture error: {e}")
                        break

                    prompt = f"""
                    You are a web agent. Goal: "{raw_task}".
                    Current Query Used: "{search_query}"
                    
                    Tools (JSON only):
                    1. {{ "action": "click", "text": "visible text" }}
                    2. {{ "action": "scroll" }}
                    3. {{ "action": "done" }} (If you see the product/answer)
                    
                    If you see a cookie banner, click 'Accept' or 'Reject'.
                    If you see a list of results, click the most relevant Link Title.
                    If you see an error or 'Try Again', try to click something else or say "done".
                    
                    Respond ONLY with JSON.
                    """
                    
                    try:
                        response = model.generate_content([prompt, img_pil])
                        text_resp = response.text.replace("```json", "").replace("```", "").strip()
                        decision = json.loads(text_resp)
                        print(f"   🤖 Thought: {decision}")
                    except:
                        print("   ⚠️ Brain fail, defaulting to scroll")
                        decision = {"action": "scroll"}

                    action_type = decision.get("action")
                    target_text = decision.get("text", "")
                    
                    if action_type == "click" and target_text == last_action_text:
                        loop_count += 1
                    else:
                        loop_count = 0
                    last_action_text = target_text

                    if loop_count >= 2:
                        print("   🔄 Loop detected (clicking same thing). Forcing Scroll.")
                        action_type = "scroll" 

                    action_log.append(f"Step {step+1}: {decision}")

                    # Exécution
                    if action_type == "click":
                        print(f"   🖱️ Clicking: {target_text}")
                        try:
                            elem = page.get_by_text(target_text, exact=False).first
                            if await elem.is_visible():
                                await elem.click(timeout=5000)
                                await page.wait_for_load_state("domcontentloaded")
                                await asyncio.sleep(2)
                            else:
                                print("   Element not visible")
                        except Exception as e:
                            print(f"   ❌ Click Failed: {e}")

                    elif action_type == "scroll":
                        print("   📜 Scrolling...")
                        await page.mouse.wheel(0, 600)
                        await asyncio.sleep(1)

                    elif action_type == "done":
                        print("   🎉 Task Completed.")
                        break
                    
                    elif action_type == "type":
                         pass 

            except Exception as e:
                print(f"❌ Critical Error: {e}")
                action_log.append(f"CRITICAL ERROR: {str(e)}")
            
            finally:
                print("📦 Closing browser and packaging evidence...")
                await browser.close()
                
                response_payload = {
                    "final_answer": "Agent finished execution.",
                    "evidence_bundle": {
                        "screenshots": screenshots_b64,
                        "action_trace": "\n".join(action_log)
                    }
                }
                
                json_response = json.dumps(response_payload)
                print(f"📤 Sending Payload ({len(json_response)} bytes)")
                await event_queue.enqueue_event(new_agent_text_message(json_response))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass

card_data = {
    "name": "smart-white-agent",
    "description": "Smart Multimodal Agent",
    "version": "1.2.0",
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

