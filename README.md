# Enjinx - AI Research Assistant

Enjinx is an AI-powered research assistant designed to help users efficiently find, analyze, and synthesize information from the web. It integrates web search capabilities with multiple AI language models and robust security features.

## Demo

Watch a demonstration of Enjinx in action:
[Enjinx Demo Video](https://drive.google.com/file/d/1qqj1R2VEQisKjowcRqr5NxXdcbpxC0kb/view?usp=sharing)


## Core Features

*   **Web Search:** Utilizes a self-hosted SearXNG instance to fetch search results from various sources.
*   **AI-Powered Analysis:** Provides in-depth analysis using a choice of AI models:
    *   Google Gemini (Cloud-based)
    *   Local Mistral model via Ollama (User-controlled, privacy-focused)
*   **Structured Output:** The AI generates a structured response including:
    *   Sub-questions explored
    *   Step-by-step analysis with citations
    *   Key synthesis points
    *   A comprehensive final answer in bullet points
    *   Cited sources
*   **User Authentication:** Secure user login and registration handled by Supabase.
*   **Chat History:** Stores conversation history for each user, managed via Supabase.
*   **Dynamic AI Model Selection:** Users can switch between available AI models via the UI.
*   **Security & Safety:**
    *   **Web Content Sanitization:** HTML is stripped from fetched web content before AI processing.
    *   **AI Input Refusal:** AI models are prompted to refuse inappropriate queries.
    *   **Output Moderation:** AI-generated final answers are scanned for disallowed content patterns.

## Technology Stack

*   **Frontend:** Next.js, TypeScript, React, Tailwind CSS
*   **Backend:** FastAPI (Python), Uvicorn
*   **Search Engine:** Self-hosted SearXNG (run via Docker)
*   **AI Language Models:**
    *   Google Gemini API
    *   Ollama for local models (e.g., Mistral)
*   **Database & Authentication:** Supabase (PostgreSQL)
*   **Content Extraction:** Python (`httpx`, `BeautifulSoup`)

## Project Structure

```
/Enjinx
├── backend/        # FastAPI application
│   ├── app/        # Core backend logic (main.py, clients, processing, etc.)
│   └── ...
├── frontend/       # Next.js application
│   ├── app/        # Next.js app router (pages, components)
│   ├── lib/        # Supabase client, etc.
│   └── ...
├── docker-compose.yml (Example for SearXNG, if used)
└── README.md
```

## Setup and Running the Project

### Prerequisites

*   Node.js and npm/yarn
*   Python 3.8+
*   Docker & Docker Compose
*   Ollama installed and a model (e.g., Mistral) pulled (`ollama pull mistral`)
*   Access to Google Gemini API key
*   Supabase project setup (URL and Anon Key)

### 1. Backend Setup

```bash
# Navigate to the backend directory
cd backend

# Create and activate a virtual environment (recommended)
python -m venv venv
# On Windows: venv\Scripts\activate
# On macOS/Linux: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt # Ensure you have a requirements.txt

# Create a .env file in the backend/ directory and add your API keys:
# GOOGLE_API_KEY=your_gemini_api_key
# OLLAMA_MODEL_NAME_MISTRAL=mistral # Or your specific Ollama model name
# OLLAMA_BASE_URL=http://localhost:11434 # If not default
# SEARXNG_URL=http://localhost:8080 # If not default (must match your SearXNG setup)
# SUPABASE_URL=your_supabase_url # If backend needs direct Supabase access (e.g., for service roles)
# SUPABASE_KEY=your_supabase_service_role_key # If backend needs direct Supabase access

# Run the FastAPI server
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install
# or
# yarn install

# Create a .env.local file in the frontend/ directory and add your Supabase keys:
# NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
# NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key

# Run the Next.js development server
npm run dev
# or
# yarn dev
```

### 3. SearXNG Setup (Docker)

It's recommended to run SearXNG via Docker. You can use a `docker-compose.yml` or run it directly.

**Example `docker-compose.yml` for SearXNG:**
```yaml
version: '3.8'
services:
  searxng:
    image: searxng/searxng:latest
    ports:
      - "8080:8080" # Host port:Container port
    volumes:
      - ./searxng_data:/etc/searxng # Persistent settings
    environment:
      - SEARXNG_BASE_URL=http://localhost:8080 # Or your public URL if exposing
    restart: unless-stopped
    container_name: searxng
```
Run with `docker-compose up -d`.

Alternatively, a simple Docker run command (less configurable):
```bash
docker run -d --name searxng -p 8080:8080 searxng/searxng:latest
```
Ensure the `SEARXNG_URL` in the backend's `.env` file matches how you expose SearXNG (e.g., `http://localhost:8080`).

### 4. Ollama Setup

1.  **Install Ollama:** Follow instructions on [ollama.com](https://ollama.com/).
2.  **Pull a model:** `ollama pull mistral` (or any other model you configure in the backend via `OLLAMA_MODEL_NAME_MISTRAL`).
3.  Ensure Ollama is running when you use the local model option in Enjinx.

## How to Use

1.  Start the backend server.
2.  Start the frontend development server.
3.  Ensure SearXNG (Docker) and Ollama (if using local models) are running.
4.  Open your browser to the frontend URL (usually `http://localhost:3000`).
5.  Sign up or log in.
6.  Select your preferred AI model (Gemini or Mistral) from the dropdown.
7.  Enter your research query and submit.
8.  Observe the AI's thinking process and review the structured analysis.

---

*This README provides a general overview. Specific configurations might vary based on your exact setup.*
