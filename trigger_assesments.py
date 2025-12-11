import asyncio
import json
from my_a2a import send_message
from a2a.utils import get_text_parts 

GREEN_AGENT_URL = "https://webjudge-project.onrender.com"
# PUT YOUR WHITE AGENT URL HERE (IT MIGHT HAVE CHANGED)
WHITE_AGENT_URL = "https://unannoyed-alda-emigrational.ngrok-free.dev" 

TASK = f"""
<white_agent_url>
{WHITE_AGENT_URL}
</white_agent_url>
<task_prompt>
What happend the 8th of september 2003 ?
</task_prompt>
<action_budget>
10
</action_budget>
"""

async def main():
    print(f"🚀 Triggering Green Agent at {GREEN_AGENT_URL}...")
    
    try:
        response = await send_message(GREEN_AGENT_URL, TASK)
        
        result = response.root.result
        text_parts = get_text_parts(result.parts)
        
        print("\n✅ Response from Green Agent:\n")
        if text_parts:
            print(text_parts[0])
        else:
            print("No text content returned.")
            
    except Exception as e:
        print(f"❌ Error in script: {e}")

if __name__ == "__main__":
    asyncio.run(main())
