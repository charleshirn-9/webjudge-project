⚖️ WebJudge: Automated Evaluation for Web Agents
WebJudge is a distributed evaluation framework designed to rigorously assess the performance of autonomous web-browsing agents.
Built on the AgentBeats A2A (Agent-to-Agent) Protocol, it employs a "Green Agent" (Evaluator) that orchestrates tasks, dispatches them to "White Agents" (Test Subjects), and grades their performance using multimodal LLMs (Google Gemini 1.5 Pro).
🌟 Architecture
The system operates in a distributed manner:
Green Agent (The Judge): Hosted in the cloud (e.g., Render). It acts as the orchestrator. It sends tasks to the White Agent and evaluates the returned evidence (screenshots & action logs) against a strict rubric.
White Agent (The Test Subject): Runs locally or on a server. It uses Playwright to perform real web navigation tasks (e.g., "Find a PS5 on Amazon") and returns execution traces.
Communication: Both agents communicate via the A2A JSON-RPC protocol, allowing for seamless interoperability with the AgentBeats platform.
🚀 Features
Active Orchestration: The Green Agent actively commands the White Agent to perform tasks.
Real Browser Navigation: Includes a reference White Agent implementation using Playwright and DuckDuckGo.
Multimodal Grading: Uses Gemini 1.5 Pro Vision to analyze screenshots and verify if constraints (price, product type, website) were met.
AgentBeats Compatible: Fully compliant with the A2A standard for integration with the AgentBeats benchmarking platform.
🛠️ Installation
Clone the repository:
code
Bash
git clone https://github.com/charleshirn-9/webjudge-project.git
cd webjudge-project
Install dependencies:
code
Bash
pip install -r requirements.txt
playwright install
Set up Environment Variables:
You need a Google Gemini API Key for the Green Agent.
code
Bash
# Windows (PowerShell)
$env:GOOGLE_API_KEY="your_gemini_api_key_here"

# Mac/Linux
export GOOGLE_API_KEY="your_gemini_api_key_here"
🏃‍♂️ Usage Guide
You can run the entire loop (Judge <-> Agent) locally or in a hybrid setup.
Option 1: The Hybrid Setup (Recommended)
Green Agent on Cloud (Render) ↔️ White Agent on Local PC (via Ngrok)
This simulates a real-world scenario where the evaluator is a remote service.
1. Start the White Agent (Local):
This agent will control your local browser.
code
Bash
python playwright_white_agent_api.py
It runs on http://localhost:8001.
2. Expose White Agent to Internet:
Use Ngrok to create a tunnel so the Cloud Green Agent can reach your Local White Agent.
code
Bash
ngrok http 8001
Copy the HTTPS URL provided by Ngrok (e.g., https://xyz.ngrok-free.app).
3. Trigger the Assessment:
Open trigger_assesments.py and update the WHITE_AGENT_URL with your Ngrok URL.
code
Bash
python trigger_assesments.py
What happens next?
The script sends a request to the Green Agent (on Render).
The Green Agent contacts your White Agent (via Ngrok).
Chromium opens on your computer, performs the search, and closes.
Evidence is sent back to the cloud.
Gemini grades the attempt.
The final Score & Verdict are printed in your terminal.
Option 2: Full Local Testing
Run everything on your machine for debugging.
Terminal 1 (Green Agent):
code
Bash
$env:PORT=9001; python main.py
Terminal 2 (White Agent):
Update AGENT_URL in playwright_white_agent_api.py to http://localhost:8001.
code
Bash
python playwright_white_agent_api.py
Terminal 3 (Trigger):
Update GREEN_AGENT_URL to http://localhost:9001 and WHITE_AGENT_URL to http://localhost:8001 in trigger_assesments.py.
code
Bash
python trigger_assesments.py
📂 Project Structure
main.py: Entry point for the Green Agent (Server). Handles A2A communication and orchestration.
green_agentv2.py: Core logic for grading (LLM prompts, task deconstruction).
playwright_white_agent_api.py: The White Agent server. Runs Playwright to execute tasks.
trigger_assesments.py: Client script to initiate a test between the two agents.
my_a2a.py: Helper utilities for the Agent-to-Agent protocol.
agent-card.toml / white-agent.toml: Metadata definitions for the agents.
🤝 Contributing
Contributions are welcome! Please ensure any new agents implement the A2A protocol correctly.
