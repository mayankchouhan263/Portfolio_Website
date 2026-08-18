"""
Portfolio Q&A chatbot backend.

Answers visitor questions about Mayank Chouhan using his resume/portfolio
info as context. Uses Groq's free-tier API (OpenAI-compatible, fast
Llama 3.1 model) when GROQ_API_KEY is set. Falls back to a simple
keyword-matching bot when no key is configured, so the demo still works
out of the box with zero setup.

Run locally:
    pip install -r requirements.txt
    export GROQ_API_KEY=your_key_here      # optional but recommended
    python app.py

Then open the portfolio site — chatbot.js already points at
http://127.0.0.1:5000/api/chat.
"""

import os
import re
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv

load_dotenv("env/.env")


app = Flask(__name__)
CORS(app)  # allow requests from the portfolio site (any origin, for simplicity)

GROQ_API_KEY = os.getenv("groq_api_key", "").strip()
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# ---------------------------------------------------------------------------
# Knowledge base: everything the bot is allowed to talk about.
# Keep this in sync with the resume / portfolio content.
# ---------------------------------------------------------------------------
PORTFOLIO_CONTEXT = """
Name: Mayank Chouhan
Role: AI & Machine Learning (AIML) undergraduate
Location: Bhopal, Madhya Pradesh, India
Contact: mayankchouhan263@gmail.com 
LinkedIn: linkedin.com/in/mayank-chouhan-714340327
GitHub: github.com/mayankchouhan263
LeetCode: leetcode.com/u/Mayank_Chouhan
Portfolio: mayankchouhan263.github.io/Portfolio_Website

PROFILE:
AIML undergraduate with hands-on experience architecting full-stack machine
learning pipelines and computer vision systems. Builds and deploys
high-accuracy predictive models and real-time object detection applications
using Python, Django, and deep learning frameworks.

TECHNICAL SKILLS:
- Programming: Python, Java, C, SQL
- Core CS: Data Structures & Algorithms, OOP, Database Management (SQL)
- Machine Learning: Scikit-learn, Classification, Regression, Ensemble
  Learning, Clustering, PCA, Anomaly Detection, Feature Engineering
- Deep Learning & Vision: PyTorch, CNN, RNN, YOLO, Faster R-CNN, OpenCV, NLP
- GenAI & NLP: Transformers, GANs, LLMs, RAG, OpenAI APIs
- Web & Deployment: HTML, CSS, JavaScript, Django, Flask, FastAPI, Render
- Tools: Git, GitHub, VS Code, JupyterLab, Canva, Figma (basic)

PROJECTS:
1. CreditWise — AI Loan Intelligence System
   Full-stack ML web app (Python, Django, Scikit-learn, Logistic Regression)
   trained on 975,800 records — 83.1% accuracy, 74.8% precision, 69.3% F1.
   End-to-end pipeline: preprocessing, feature engineering (Credit Score^2,
   DTI^2, Collateral Ratio), model training, REST API integration.
   Deployed on Render with WhiteNoise + Gunicorn. Frontend has an EMI
   calculator, amortization schedule, and real-time prediction.
   Live: creditwise-rxt6.onrender.com | Repo: github.com/mayankchouhan263/CreditWise

2. Autonomous Flappy Bird Agent — Deep Q-Networks (DQN)
   Reinforcement learning agent that learns to play Flappy Bird from
   scratch using a Deep Q-Network built in PyTorch on the Flappy Bird
   Gymnasium environment. Implements experience replay, target-network
   synchronization, epsilon-greedy exploration, Double DQN, gradient
   clipping, and YAML-configurable hyperparameters, with checkpointing
   across CPU/CUDA/MPS.
   Repo: github.com/mayankchouhan263/Autonomous-Flappy-Bird-Agent-with-Deep-Q-Networks

3. SmartCart — Customer Segmentation System
   Unsupervised ML system for an e-commerce platform (SmartCart) that
   clusters 2,240 customers across 22 behavioural/demographic attributes
   using K-Means and hierarchical clustering, with a full pipeline of
   preprocessing, EDA, feature engineering, and cluster visualization for
   personalized marketing, retention, and churn analysis.
   Repo: github.com/mayankchouhan263/SmartCart-Clustering-System

4. Real-Time Object Detection System
   Combines YOLO, SSD, Faster R-CNN, and a custom CNN in Python. Trained and
   fine-tuned on custom datasets (preprocessing, augmentation, mAP@0.5
   evaluation). OpenCV integration for webcam-based live detection with
   bounding-box visualization.

5. SOS Game with Minimax AI
   Classic SOS board game built in Python with Pygame, integrating a custom
   Minimax algorithm as the AI opponent.
   Repo: github.com/mayankchouhan263/SOS_Game

6. Portfolio Website
   Responsive site built with HTML5, CSS3, vanilla JS, deployed on GitHub
   Pages, now including this chatbot.
   Repo: github.com/mayankchouhan263/Portfolio_Website

Also on GitHub: Learning_AIML (ongoing notebooks covering ML/DL/RL/NLP/
GenAI/RAG fundamentals) and Python_DSA_Problems (DSA practice repo),
both at github.com/mayankchouhan263.

CERTIFICATIONS:
- Prime AIML Batch (4-Month Intensive) — Apna College
- CCNA Series (Enterprise, Routing & Switching), Python Essentials 1 & 2,
  Modern AI, Data Science & IoT — Cisco Networking Academy
- Prompt Design in Vertex AI Skill Badge — Google Cloud
- OpenEDG Python Professional, GenAI, Python (Essential/OOP/Level Up),
  JavaScript & AI Fundamentals — LinkedIn Learning

ACHIEVEMENTS:
- GATE 2026 — All India Rank (AIR): 18644
- Qualified TCS CodeVita Round 2
- Solved 200+ Data Structures & Algorithms problems across platforms

EDUCATION:
- B.Tech, Artificial Intelligence & Machine Learning — Lakshmi Narain
  College of Technology (LNCT), Bhopal. 2023-2027 (expected). CGPA 8.03/10.
- Higher Secondary (CBSE, Science/PCM) — St. Mary's Convent School,
  Petlawad. 2022. 76.6%.
- Secondary (CBSE) — St. Mary's Convent School, Petlawad. 2020. 86.4%.

VISION:
Wants to apply software engineering, AI, and ML skills to build innovative,
real-world solutions with meaningful impact — technology that is
intelligent, scalable, ethical, and genuinely useful.
"""

SYSTEM_PROMPT = f"""You are the assistant embedded in Mayank Chouhan's portfolio website.
Answer visitor questions about Mayank using ONLY the information below.
Be concise (2-4 sentences unless asked for detail), friendly, and factual.
If asked something not covered by this information (personal opinions,
unrelated topics, or anything you don't know), say you don't have that
information and suggest contacting Mayank directly at
mayankchouhan263@gmail.com.
Never invent facts, numbers, or links that aren't in the context.

CONTEXT ABOUT MAYANK:
{PORTFOLIO_CONTEXT}
"""


def call_groq(message, history):
    """Call Groq's free-tier chat completions API. Raises on failure."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in history[-6:]:  # keep last few turns for context
        role = "user" if turn.get("role") == "user" else "assistant"
        messages.append({"role": role, "content": turn.get("content", "")})
    messages.append({"role": "user", "content": message})

    resp = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": GROQ_MODEL,
            "messages": messages,
            "temperature": 0.4,
            "max_tokens": 400,
        },
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


@app.route("/api/chat", methods=["POST"])
def chat():
    body = request.get_json(silent=True) or {}
    message = (body.get("message") or "").strip()
    history = body.get("history") or []

    if not message:
        return jsonify({"reply": "Ask me something about Mayank's skills, projects, or background!"})

    if GROQ_API_KEY:
        reply = call_groq(message, history)
        return jsonify({"reply": reply, "mode": "llm"})



@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "llm_configured": bool(GROQ_API_KEY)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
