# WebJudge: Automated Evaluation for Web Agents

**WebJudge** is an automated framework designed to rigorously evaluate the performance of autonomous web-browsing agents. 

It employs a "Green Agent" (powered by Multimodal LLMs like **Google Gemini 1.5 Pro** or **GPT-4o**) to grade "White Agents" (the agents being tested) on complex, real-world tasks. The evaluation is based on a strict, evidence-based rubric that assesses task success, constraint satisfaction, and efficiency.

## 🚀 Features

*   **Automated Rubric Grading:** Scores agents on Goal Completion, Constraint Adherence, Efficiency, and Evidence Quality.
*   **Multi-Modal Analysis:** Analyzes both text-based action logs and visual screenshots to verify agent claims.
*   **Interactive Testing CLI:** A user-friendly command-line interface to manually test and debug agent outputs.
*   **Flexible Backend:** Compatible with Google Gemini and OpenAI models.

## 🛠️ Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/YOUR_USERNAME/WebJudge.git
    cd WebJudge
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## 🔑 Configuration

You need to set up your API key for the LLM provider you are using (default is Google Gemini).

**For Windows (Command Prompt):**
```cmd
set GOOGLE_API_KEY="your_actual_api_key_here"
