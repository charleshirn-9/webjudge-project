from green_agentv2 import evaluate_white_agent_output 
import json
import os

def load_action_trace(path):
    """Loads the action trace from a text file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ ERROR: The file '{path}' was not found.")
        return None

def get_user_input():
    """Guides the user to provide all necessary inputs for the evaluation."""
    
    print("---  interactive WebJudge Test ---")
    print("Please provide the details for the evaluation.")

    task_prompt = input("\n[1] Enter the Task Prompt for the agent:\n> ")

    while True:
        try:
            action_budget_str = input("\n[2] Enter the Action Budget (e.g., 10):\n> ")
            action_budget = int(action_budget_str)
            break
        except ValueError:
            print("❌ Invalid input. Please enter a whole number.")

    screenshot_paths = []
    print("\n[3] Enter the paths to the screenshot files.")
    print("   (Drag and drop files into the terminal or type the full path. Press Enter after each one.)")
    print("   (Type 'done' when you have added all screenshots.)")
    while True:
        path = input(f"   Screenshot {len(screenshot_paths) + 1}: > ").strip().replace("'", "") 
        if path.lower() == 'done':
            if not screenshot_paths:
                print("⚠️ Warning: No screenshots provided.")
            break
        
        # Simple validation to check if the file exists
        if os.path.exists(path):
            screenshot_paths.append(path)
            print(f"   ✅ Added: {path}")
        else:
            print(f"   ❌ ERROR: File not found at '{path}'. Please try again.")

    # 4. Get Action Trace Path
    action_trace = ""
    while True:
        trace_path = input("\n[4] Enter the path to the action_trace.txt file:\n> ").strip().replace("'", "")
        
        trace_content = load_action_trace(trace_path)
        if trace_content is not None:
            action_trace = trace_content
            print(f"   ✅ Loaded action trace from: {trace_path}")
            break
        # Loop will continue if load_action_trace returns None (file not found)
        
    # Assemble the final payload
    white_agent_payload = {
        "task_prompt": task_prompt,
        "action_budget": action_budget,
        "evidence_bundle": {
            "screenshots": screenshot_paths,
            "action_trace": action_trace
        }
    }
    
    return white_agent_payload


if __name__ == "__main__":
    # Get all inputs interactively from the user
    payload = get_user_input()
    
    if payload:
        print("\n========================================================")
        print("🚀 Sending the following payload to the Green Agent for evaluation...")
        print("========================================================")
        # Run the evaluation with the user-provided payload
        final_grade = evaluate_white_agent_output(payload)