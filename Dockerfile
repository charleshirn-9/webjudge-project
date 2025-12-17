FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python -m playwright install chromium

CMD ["python", "smart_white_agentv2.py"]
