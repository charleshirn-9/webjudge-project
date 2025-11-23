import base64
import requests
import time
from playwright.sync_api import sync_playwright

# Configuration
GREEN_AGENT_URL = "http://127.0.0.1:8000/evaluate" 
def screenshot_to_base64(screenshot_bytes):
    """Helper to convert raw image bytes to a base64 string for the API."""
    return base64.b64encode(screenshot_bytes).decode('utf-8')

def run_naive_agent():
    print("--- 🤖 Interactive White Agent ---")
    task_prompt = input("\n[?] What task do you want the White Agent to perform?\n> ").strip()
    
    if not task_prompt:
        print("❌ No task provided. Exiting.")
        return

    try:
        budget_input = input("\n[?] Enter action budget (default 10):\n> ").strip()
        action_budget = int(budget_input) if budget_input else 10
    except ValueError:
        action_budget = 10

    print(f"\n🚀 Starting task: '{task_prompt}' with budget {action_budget}...")
    
    action_log = []
    screenshots_b64 = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=1000)
        page = browser.new_page()

        try:
            # --- ACTION 1: Go to Search Engine (DuckDuckGo to avoid Captcha) ---
            print("Step 1: Navigating to DuckDuckGo...")
            page.goto("https://duckduckgo.com")
            action_log.append("1. Navigated to https://duckduckgo.com")
            
            # Take screenshot 1
            img = page.screenshot()
            screenshots_b64.append(screenshot_to_base64(img))

            # --- ACTION 2: Search for the task ---
            print(f"Step 2: Searching for '{task_prompt}'...")
            
            # DuckDuckGo search bar selector
            page.fill("input[name='q']", task_prompt)
            page.press("input[name='q']", "Enter")
            action_log.append(f"2. Searched for: '{task_prompt}'")
            
            page.wait_for_load_state("networkidle")
            
            # Take screenshot 2 (Results)
            img = page.screenshot()
            screenshots_b64.append(screenshot_to_base64(img))

            # --- ACTION 3: Click the first result ---
            print("Step 3: Clicking first result...")
            
            
            try:
                with page.expect_navigation(timeout=15000):
                    page.click("a[data-testid='result-title-a'] >> nth=0")
                
                current_url = page.url
                action_log.append(f"3. Clicked the first result. Landed on: {current_url}")
                print(f"📍 Arrived at: {current_url}")

            except Exception as e:
                print("⚠️ Could not click first result (maybe no results found).")
                action_log.append("3. Failed to click on a result.")

            # Take final screenshot
            page.wait_for_load_state("domcontentloaded")
            time.sleep(3) 
            img = page.screenshot()
            screenshots_b64.append(screenshot_to_base64(img))
            
        except Exception as e:
            print(f"⚠️ Agent encountered an error: {e}")
            action_log.append(f"ERROR: {str(e)}")
        
        finally:
            browser.close()

    # --- SEND TO GREEN AGENT ---
    print("\n📦 Packaging evidence and sending to Green Agent...")
    
    payload = {
        "task_prompt": task_prompt,
        "action_budget": action_budget,
        "evidence_bundle": {
            "screenshots": screenshots_b64,
            "action_trace": "\n".join(action_log)
        }
    }

    try:
        response = requests.post(GREEN_AGENT_URL, json=payload)
        
        if response.status_code == 200:
            grade = response.json()
            print("\n✅ ---------------- JUDGEMENT RECEIVED ---------------- ✅")
            print(f"Verdict: {grade.get('final_verdict')}")
            print(f"Total Score: {grade.get('total_score')}/100")
            print("-------------------------------------------------------")
            print("Detailed Scores:")
            rubric = grade.get('rubric_scores', {})
            for category, details in rubric.items():
                print(f" - {category}: {details.get('score')} pts")
                print(f"   Reason: {details.get('reasoning')}")
            print("-------------------------------------------------------")
            print(f"Summary: {grade.get('summary_reasoning')}")
        else:
            print(f"❌ Error from Green Agent (Status {response.status_code}): {response.text}")

    except Exception as e:
        print(f"❌ Failed to connect to Green Agent. Is 'main.py' running? Error: {e}")

if __name__ == "__main__":
    run_naive_agent()