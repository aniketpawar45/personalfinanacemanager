# Personal Finance Manager

A Python-based personal finance management application with Telegram bot integration, automated email reporting, and AI-powered transaction insights.

## 🌟 Overview

Personal Finance Manager is a streamlined backend system that allows users to track expenses and manage personal cash flow straight from a Telegram chat interface. It utilizes advanced Large Language Models (LLMs) to automatically parse natural text and voice notes into structured database records, complete with dynamic category tagging and graphical analytics visualization.

## ✨ Features

* **AI-Powered Natural Text Parsing** – Automatically extracts amounts, item descriptions, and categories from text inputs like `"Coffee 40, Bread 30"`.
* **Voice Note Transcription** – Transcribes sent voice messages into structured transaction logging using Groq Whisper.
* **Visual Charts & Heatmaps** – Generates high-contrast expense profile breakdown charts via QuickChart integrations.
* **Automated Email Reports** – Schedules zero-persistence CSV financial reports routed directly to specified inbox channels.
* **Serverless Backend Architecture** – Fast, scalable REST API built on FastAPI and fully optimized for serverless edge routing.

---

## 🛠️ Tech Stack

* **Backend Framework:** FastAPI & Uvicorn
* **Database Client:** Supabase (PostgreSQL)
* **AI Compute Client:** Groq SDK (`llama-3.1-8b-instant` & `whisper-large-v3`)
* **Telegram Pipeline:** `python-telegram-bot`
* **Hosting Layer:** Vercel

---

## 🚀 Local Installation & Setup

### 1. Prerequisites
Ensure you have the following installed locally:
* Python 3.8+
* Pip or Conda package manager

### 2. Project Initialization
```bash
# Clone the repository
git clone [https://github.com/aniketpawar45/personalfinanacemanager.git](https://github.com/aniketpawar45/personalfinanacemanager.git)
cd personalfinanacemanager

# Configure your virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install -r requirements.txt