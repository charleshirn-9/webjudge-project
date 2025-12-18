# ⚖️ WebJudge: Automated Evaluation for Web Agents

**WebJudge** is a distributed evaluation framework designed to rigorously assess the performance of autonomous web-browsing agents.

Built on the **AgentBeats A2A (Agent-to-Agent) Protocol**, it employs a **"Green Agent"** (Evaluator) that orchestrates tasks, dispatches them to **"White Agents"** (Test Subjects), and grades their performance using multimodal LLMs (Gemini).

## 🌟 Architecture

The system operates in a distributed manner:

1.  **Green Agent (The Judge):** Hosted in the cloud (Render). It acts as the orchestrator. It sends tasks to the White Agent and evaluates the returned evidence (screenshots & action logs) against a strict rubric.
2.  **White Agent (The Test Subject):** Runs locally or on a server (via Docker). It uses **Playwright** to perform real web navigation tasks.
    *   *Naive Agent:* Simple search and click.
    *   *Smart Agent:* Autonomous navigation using Vision and LLM reasoning.
3.  **Communication:** Both agents communicate via the **A2A JSON-RPC protocol**, allowing for seamless interoperability with the AgentBeats platform.

## 🚀 Features

*   **Active Orchestration:** The Green Agent actively commands the White Agent to perform tasks.
*   **Smart Vision Navigation:** Includes an autonomous White Agent that "sees" the page and decides actions dynamically.
*   **Multimodal Grading:** Uses Gemini to analyze screenshots and verify if constraints (price, product type, website) were met.
*   **Docker Support:** Ready for cloud deployment (Render/AWS) using the included `Dockerfile`.

---

## 🛠️ Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/charleshirn-9/webjudge-project.git
    cd webjudge-project
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    playwright install
    ```

3.  **Set up Environment Variables:**
    You need a Google Gemini API Key for the Green Agent (and Smart White Agent).
    ```bash
    # Windows (PowerShell)
    $env:GOOGLE_API_KEY="your_gemini_api_key_here"
    
    # Mac/Linux
    export GOOGLE_API_KEY="your_gemini_api_key_here"
    ```

---

## 🏃‍♂️ Usage Guide

You can run the loop in a **Hybrid** setup (Cloud Green Agent <-> Local White Agent) or **Full Cloud**.

### Option 1: Hybrid Setup (Recommended for Dev)
*Green Agent on Cloud (Render) ↔️ White Agent on Local PC (via Ngrok)*

1.  **Start a White Agent (Choose one):**
    *   **Smart Agent (Autonomous):**
        ```bash
        python smart_white_agentv2.py
        ```
    *   **Naive Agent (Simple Script):**
        ```bash
        python playwright_white_agent_api.py
        ```
    *(Runs on `http://localhost:8001`)*

2.  **Expose White Agent to Internet:**
    Use Ngrok to create a tunnel so the Cloud Green Agent can reach your PC.
    ```bash
    ngrok http 8001
    ```
    *Copy the HTTPS URL provided by Ngrok (e.g., `https://xyz.ngrok-free.app`).*

3.  **Update Configuration:**
    *   Update the `AGENT_URL` variable inside your chosen White Agent python script with the Ngrok URL.
    *   Restart the python script.

4.  **Trigger the Assessment:**
    Open `trigger_assesments.py`, update `WHITE_AGENT_URL` with your Ngrok URL, and run:
    ```bash
    python trigger_assesments.py
    ```

### Option 2: Full Cloud Setup (Render)
*Green Agent (Render) ↔️ White Agent (Render Docker)*

1.  Deploy the repository to Render as a **Web Service** using `Docker` runtime.
2.  Update `trigger_assesments.py` with the Render URL of your White Agent.
3.  Run the trigger script.

---

## 📂 Project Structure

*   `main.py`: **Green Agent Server**. Handles A2A communication and orchestration.
*   `green_agentv2.py`: Core grading logic (LLM prompts, task deconstruction).
*   `smart_white_agentv2.py`: **Smart White Agent**. Uses Gemini Vision + Playwright to navigate websites autonomously.
*   `playwright_white_agent_api.py`: **Naive White Agent**. Performs basic search queries.
*   `trigger_assesments.py`: Client script to initiate a test between the two agents.
*   `Dockerfile`: Configuration for deploying the White Agent on Render
*   `my_a2a.py`: Helper utilities for the Agent-to-Agent protocol.
*   `agent-card.toml` / `white-agent.toml`: Metadata definitions for the agents.

## 🤝 Contributing

Contributions are welcome! Please ensure any new agents implement the A2A protocol correctly.
