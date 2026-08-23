# UNI: AI-Powered Product Data Enrichment Pipeline

UNI is an intelligent, containerized batch-processing pipeline designed to clean, standardize, and enrich messy product catalog data. 

It takes raw, unstructured product inputs (e.g., messy descriptions, sparse manufacturer data) and outputs highly structured, validated, and normalized product attributes using a hybrid approach of deterministic Regex extraction and LLM-powered data synthesis via LangGraph.

## 🚀 Key Features

- **Hybrid Extraction Engine:** Uses deterministic Python Regex to extract math-heavy attributes (dimensions, fractions, voltages) with 100% confidence before handing off to the LLM.
- **LangGraph Architecture:** Breaks the LLM synthesis down into focused state-machine nodes, preventing hallucination and format drift.
- **Strict Data Validation:** Built-in rules engine (MPN checks, dimension checks) that scores output data.
- **Human-in-the-Loop Safeguards:** Automatically splits results into `enriched.csv`, `warning.csv`, and `failed.csv` so human reviewers only have to look at edge cases.
- **Real-Time UI:** A sleek React frontend that provides real-time progress of batch jobs via Server-Sent Events (SSE) and allows detailed inspection of enriched records.

## 🛠️ Technology Stack

- **Frontend:** React, TypeScript, Vite, Astryx Design System, Zustand (State Management)
- **Backend API:** Python, FastAPI, Pydantic (Strict Schema Enforcement)
- **AI / Pipeline:** LangGraph, Google Gemini 1.5 Pro
- **Task Queue:** Celery, Redis
- **Infrastructure:** Fully Dockerized (Docker Compose)

---

## 🏃 Getting Started

The entire application stack is orchestrated via Docker Compose. You do not need to install Node, Python, or Redis on your host machine.

### Prerequisites
- Docker & Docker Compose installed.
- A valid Gemini API Key (`GEMINI_API_KEY`).

### 1. Setup Environment Variables
Create a `.env` file in the `backend/` directory:
```bash
cd backend
touch .env
```
Add your Gemini API Key to the `.env` file:
```env
GEMINI_API_KEY=your_api_key_here
```

### 2. Launch the Stack
From the root directory of the project, run:
```bash
docker-compose up --build
```
This will spin up:
- **Redis Server** (Port 6379)
- **Celery Worker** (Background Task Processor)
- **FastAPI Backend** (`http://localhost:8000`)
- **React Frontend** (`http://localhost:5173`)

### 3. Use the Application
Open your browser and navigate to `http://localhost:5173`.
1. Click **Upload CSV** and provide a raw product data file.
2. Watch the real-time progress bar as the Celery workers process the rows.
3. Click on individual rows to inspect the raw vs. enriched data.
4. When finished, download the main enriched CSV, along with any flagged Warnings or Failures.

---

## 🏗️ Architecture Flow

1. **Upload:** User uploads a CSV. FastAPI saves it and queues a `batch_enrichment` task in Celery/Redis.
2. **Extraction:** The worker parses the row. `extractor.py` uses Regex to pull out high-confidence physical dimensions and specifications.
3. **Synthesis:** LangGraph passes the raw data + regex extractions to Gemini. Gemini normalizes brand names, synthesizes missing data, and categorizes the product into strict Pydantic JSON schemas.
4. **Validation:** `validator.py` applies business logic rules to the output. If a rule fails (e.g., "Has Valid Dimensions"), the product is flagged as a Warning.
5. **Streaming:** Progress and success/warning/failure states are streamed back to the frontend in real-time.
