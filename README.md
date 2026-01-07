# Olifan Group AI Assistant

A complete RAG (Retrieval-Augmented Generation) system for Olifan Group's customer service and information assistance.

## Project Structure

```
Olifan/
├── app/                      # Next.js Frontend
│   ├── page.tsx             # Main chat interface
│   ├── layout.tsx           # Layout component
│   └── globals.css          # Global styles
├── backend/                  # Python Backend Services
│   ├── olifan_scraper.py    # Olifan Group website scraper
│   ├── olifan_data_processor.py  # Data processing pipeline
│   ├── olifan_backend_api.py     # FastAPI service
│   ├── start_system.py      # Startup utility
│   ├── integration_test.py  # Testing suite
│   ├── requirements.txt     # Python dependencies
│   └── README.md           # Backend documentation
├── components/              # UI Components
│   └── ui/                 # Shadcn/UI components
├── lib/                    # Utility functions
├── styles/                 # CSS files
├── PROJECT_README.md       # Detailed project documentation
└── package.json           # Frontend dependencies
```

## Quick Start

### Backend Setup
```bash
cd backend
pip install -r requirements.txt

# Set environment variables:
export GROQ_API_KEY="your-groq-api-key"
export TAVILY_API_KEY="your-tavily-api-key"

# Or create a .env file:
cp .env.example .env
# Edit .env to add your API keys

python start_system.py
```

### Frontend Setup
```bash
npm install
npm run dev
```

Visit `http://localhost:3000` for the frontend and `http://localhost:8000` for the API.

## Features

- 🤖 AI-powered chat assistant
- 🔍 Semantic search over Olifan website content
- 🗣️ Voice input/output capabilities
- 🌐 Multilingual support (French/English)
- 💬 Conversation history preservation
- 🔧 External search fallback (Tavily)
- 📊 Source attribution for responses

## Architecture

```
User → Next.js Frontend → FastAPI Backend → 
FAISS Vector Store + Groq LLM + Tavily Search → 
Context-Aware Responses
```