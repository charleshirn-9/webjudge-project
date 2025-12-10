# --- START OF FILE green_agent.py (Gemini Version) ---

import os
import json
import google.generativeai as genai
from PIL import Image
import io
import base64


try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
except KeyError:
    print("❌ ERROR: The GOOGLE_API_KEY environment variable is not set.")
    exit()


model = genai.GenerativeModel('gemini-flash-latest')

def deconstruct_task_to_key_points(task_prompt: str) -> list:
    """Uses Gemini to convert a natural language task into a list of key, verifiable points."""
    system_prompt = """
    You are an expert system designed to deconstruct a user's task into a list of specific, verifiable constraints.
    Analyze the user's request and extract every distinct requirement that must be met for the task to be considered successful.
    Each constraint should be a short, clear statement.
    Return the constraints as a JSON object with a single key "constraints" containing a list of strings.
    Example Task: 'Find the newest refrigerator that is 34–36 inches wide, priced between $1,000 and $2,000, and has a customer review rating of 4 stars or higher.'
    Example Output:
    {
      "constraints": [
        "Sort by 'Newest'",
        "Filter by width: 34-36 inches",
        "Filter by price: $1,000 - $2,000",
        "Filter by rating: 4 stars or higher"
      ]
    }
    """
    
    # 3. Switched to Gemini model call with JSON output config
    # We instruct the model to only output JSON.
    generation_config = genai.GenerationConfig(response_mime_type="application/json")
    
    prompt = f"{system_prompt}\n\nHere is the task: {task_prompt}"
    
    try:
        response = model.generate_content(prompt, generation_config=generation_config)
        data = json.loads(response.text)
        key_points = data["constraints"]
        print(f"✅ Deconstructed Task into Key Points: {key_points}")
        return key_points
    except (json.JSONDecodeError, KeyError, Exception) as e:
        print(f"❌ Error parsing key points from Gemini: {e}")
        return []

def grade_agent_performance(key_points: list, screenshots: list, action_log: str, actions_taken: int, action_budget: int) -> dict:
    """
    Uses Gemini Vision to grade the agent's performance based on a detailed rubric.
    """
    
    image_parts = []
    for img_data in screenshots:
        try:
            if isinstance(img_data, str):
                if len(img_data) > 200: 
                    if "base64," in img_data:
                        img_data = img_data.split("base64,")[1]
                    
                    image_bytes = base64.b64decode(img_data)
                    image_parts.append(Image.open(io.BytesIO(image_bytes)))
                
                else:
                    image_parts.append(Image.open(img_data))
        except Exception as e:
            print(f"⚠️ Error processing an image: {e}")
            continue

    system_prompt = """
    You are an automated evaluator for web-browsing agents. Your task is to grade an agent's performance based on the provided evidence and a strict rubric.
    You must score the agent out of 100 points and provide a final verdict ('SUCCESS' or 'FAILURE').

    ### Rubric (100 points total)
    1.  **Goal Completion (40 points):**
        - 40 pts: The agent reached a final page/product that correctly satisfies ALL critical constraints.
        - Between 1-39 pts: The agent partially met the goal, satisfying some constraints but not all. Give proportional points based on how well it performed.
        - 0 pts: The final product is incorrect.
    2.  **Constraint Adherence (40 points):**
        - Award points proportionally for each constraint from the list that is verifiably met in the evidence.
        - **CRITICAL RULE:** If a critical constraint (e.g., price, rating, specific item attribute) is violated, this ENTIRE section scores 0 points, leading to an automatic task failure.
    3.  **Efficiency (10 points):**
        - 10 pts: Actions taken are less than or equal to the action budget.
        - 0 pts: Actions taken exceed the action budget.
    4.  **Evidence Quality (10 points):**
        - 10 pts: The screenshots and action log provide clear, unambiguous proof for the final decision.
        - 5 pts: The evidence is present but confusing or incomplete.
        - 0 pts: The evidence does not support the agent's final answer.

    ### Final Verdict
    - **SUCCESS:** The total score is > 80 AND no critical constraints were violated.
    - **FAILURE:** The total score is <= 80 OR any critical constraint was violated.

    You MUST respond in a valid JSON format with the following structure:
    {
      "rubric_scores": {
        "goal_completion": {"score": <number>, "reasoning": "<text>"},
        "constraint_adherence": {"score": <number>, "reasoning": "<text>"},
        "efficiency": {"score": <number>, "reasoning": "<text>"},
        "evidence_quality": {"score": <number>, "reasoning": "<text>"}
      },
      "total_score": <number>,
      "final_verdict": "<'SUCCESS' or 'FAILURE'>",
      "summary_reasoning": "<A brief, overall summary of the performance.>"
    }
    """
    
    user_prompt = f"""
    Please evaluate the following agent's performance based on the attached screenshots and the provided information.

    **System Instructions:**
    {system_prompt}

    **Task Constraints to Verify:**
    {json.dumps(key_points, indent=2)}

    **Efficiency Constraints:**
    - Action Budget: {action_budget}
    - Actions Taken: {actions_taken}

    **Agent's Evidence:**
    - Action Log: "{action_log}"
    - Screenshots are attached.
    """
    
    # 4. Assembled a multi-part prompt (text + images) for Gemini
    prompt_parts = [user_prompt] + image_parts
    generation_config = genai.GenerationConfig(response_mime_type="application/json")

    try:
        response = model.generate_content(prompt_parts, generation_config=generation_config)
        evaluation = json.loads(response.text)
        print("✅ Grading Complete.")
        return evaluation
    except (json.JSONDecodeError, KeyError, Exception) as e:
        print(f"❌ Error parsing grading results from Gemini: {e}")
        return {"final_verdict": "FAILURE", "summary_reasoning": "Error during evaluation."}


def evaluate_white_agent_output(white_agent_payload: dict) -> dict:
    """
    Main function for the Green Agent. Receives a payload and returns a scored evaluation.
    This high-level function does not need to change.
    """
    print("--- 🚀 Starting Green Agent Evaluation ---")
    
    task_prompt = white_agent_payload.get("task_prompt")
    action_budget = white_agent_payload.get("action_budget")
    evidence = white_agent_payload.get("evidence_bundle", {})
    screenshots = evidence.get("screenshots", [])
    action_trace = evidence.get("action_trace", "")

    if not all([task_prompt, action_budget, screenshots, action_trace]):
        return {"status": "error", "message": "Payload is missing required fields."}
    
    key_points = deconstruct_task_to_key_points(task_prompt)
    if not key_points:
         return {"status": "error", "message": "Could not deconstruct task into key points."}

    actions_taken = len(action_trace.strip().split('\n'))
    
    evaluation_result = grade_agent_performance(
        key_points, screenshots, action_trace, actions_taken, action_budget
    )
    
    print("--- ✅ Evaluation Finished ---")
    print(json.dumps(evaluation_result, indent=2))
    return evaluation_result

# --- END OF FILE green_agent.py (Gemini Version) ---


