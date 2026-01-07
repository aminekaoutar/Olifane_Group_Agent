# Olifan Backend Services

This folder contains all backend components for the Olifan Group AI Assistant.

## Components

- **olifan_scraper.py** - Web scraper for olifangroup.com content
- **olifan_data_processor.py** - Processes scraped data into FAISS vector store
- **olifan_backend_api.py** - FastAPI service serving the RAG agent
- **start_system.py** - Startup script for easy deployment
- **integration_test.py** - Testing suite for all components
- **requirements.txt** - Python dependencies

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables:
   ```bash
   export GROQ_API_KEY="your-groq-api-key"
   export TAVILY_API_KEY="your-tavily-api-key"
   ```
   
   Or create a .env file based on .env.example:
   ```bash
   cp .env.example .env
   # Edit .env to add your API keys
   ```

3. Run the system:
   ```bash
   python start_system.py
   ```

## Project Structure

```
backend/
├── olifan_scraper.py          # Website scraping
├── olifan_data_processor.py   # Data processing
├── olifan_backend_api.py      # API service
├── start_system.py           # Startup utility
├── integration_test.py       # Tests
└── requirements.txt          # Dependencies
```