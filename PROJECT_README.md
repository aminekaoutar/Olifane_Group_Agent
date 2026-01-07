# Olifan Group AI Assistant - Complete Integration Guide

This repository contains a complete RAG (Retrieval-Augmented Generation) system that integrates web scraping, vector storage, and AI chat functionality for Olifan Group.

## Architecture Overview

```
Frontend (Next.js) ↔ Backend API (FastAPI) ↔ RAG Engine (LangChain) ↔ Data Source (Olifan Website)
```

## Components

### 1. Web Scraping (`olifan_scraper.py`)
- Scrapes content from olifangroup.com using crawl4ai
- Extracts text content and images
- Performs OCR on images to extract text
- Saves data to `olifan_scraped_data.json`

### 2. Data Processing (`olifan_data_processor.py`)
- Loads scraped data
- Creates LangChain documents
- Splits documents into chunks
- Builds FAISS vector store
- Saves to `olifan_faiss.index` and `olifan_index_mapping.pkl`

### 3. Backend API (`olifan_backend_api.py`)
- FastAPI service serving the RAG agent
- Handles chat requests with conversation history
- Integrates Groq LLM with Tavily search tool
- Provides health checks and source inspection endpoints

### 4. Frontend (Next.js)
- React-based chat interface
- Voice input/output capabilities
- Real-time chat with loading states
- French/English bilingual support

## Setup Instructions

### Prerequisites
1. Python 3.8+
2. Node.js 16+
3. Tesseract OCR installed (for image text extraction)
4. API Keys:
   - Groq API Key
   - Tavily API Key

### Environment Variables
The system requires the following environment variables to be set:

- `GROQ_API_KEY`: Your Groq API key for LLM access
- `TAVILY_API_KEY`: Your Tavily API key for search functionality

You can set these in multiple ways:

1. **Direct environment variables**:
   ```bash
   export GROQ_API_KEY="your-groq-api-key"
   export TAVILY_API_KEY="your-tavily-api-key"
   ```

2. **Using .env file**:
   Copy the `.env.example` file to `.env` and add your keys:
   ```bash
   cp backend/.env.example .env
   # Edit .env to add your API keys
   ```

3. **System environment variables**:
   Set them in your system's environment variables

The application will automatically load from a `.env` file if python-dotenv is installed.

### Installation Steps

#### 1. Backend Setup
```bash
cd crawl4ai-youtube

# Install Python dependencies
pip install -r requirements.txt

# Set environment variables
export GROQ_API_KEY="your-groq-api-key"
export TAVILY_API_KEY="your-tavily-api-key"
```

#### 2. Scrape Olifan Website
```bash
python olifan_scraper.py
```
This creates `olifan_scraped_data.json` and downloads images.

#### 3. Process Data into Vector Store
```bash
python olifan_data_processor.py
```
This creates `olifan_faiss.index` and `olifan_index_mapping.pkl`.

#### 4. Start Backend API
```bash
python olifan_backend_api.py
```
The API will be available at `http://localhost:8000`

#### 5. Frontend Setup
```bash
# Install frontend dependencies
npm install

# Start development server
npm run dev
```
The frontend will be available at `http://localhost:3000`

## API Endpoints

### POST `/chat`
Main chat endpoint for user interactions.

**Request:**
```json
{
  "message": "Qu'est-ce que l'ingénierie patrimoniale?",
  "history": [
    {"role": "user", "content": "Bonjour"},
    {"role": "assistant", "content": "Bonjour! Comment puis-je vous aider?"}
  ]
}
```

**Response:**
```json
{
  "response": "L'ingénierie patrimoniale chez Olifan consiste à...",
  "sources": [
    {
      "content": "Extrait du contenu pertinent...",
      "url": "https://olifangroup.com/services"
      "title": "Nos Services",
      "type": "text"
    }
  ]
}
```

### GET `/health`
Health check endpoint showing component status.

### GET `/sources`
Debug endpoint to inspect indexed sources.

## Usage Flow

1. **Data Collection**: Run scraper to gather latest Olifan Group website content
2. **Index Building**: Process scraped data into searchable vector store
3. **API Deployment**: Start backend service with loaded vector store
4. **Frontend Access**: Users interact through web interface
5. **Conversation Flow**:
   - User sends message
   - Frontend calls backend API
   - Backend retrieves relevant documents using FAISS
   - LLM generates response using retrieved context
   - Response sent back to frontend

## Features

- **Multilingual Support**: Handles both French and English queries
- **Voice Interface**: Speech-to-text input and text-to-speech output
- **Conversation Memory**: Maintains chat history for context
- **External Search**: Falls back to Tavily search for current information
- **Source Attribution**: Provides sources for generated responses
- **Error Handling**: Graceful degradation when services are unavailable

## Customization

### Modifying Scraping Targets
Edit `olifan_scraper.py`:
- Change `base_url` to target different websites
- Modify `additional_pages` list to include specific URLs
- Adjust `MAX_PAGES` for larger/smaller crawls

### Tuning RAG Parameters
Edit `olifan_data_processor.py`:
- Adjust `chunk_size` and `chunk_overlap` in text splitter
- Change embedding model in `SentenceTransformerEmbeddings`
- Modify `k` parameter in similarity search

### Updating Prompts
Edit `olifan_backend_api.py`:
- Modify `system_prompt` for different assistant behavior
- Adjust tone and personality of responses
- Customize context formatting

## Troubleshooting

### Common Issues

1. **Tesseract Not Found**
   - Ensure Tesseract is installed and path is correct
   - Update `TESSERACT_PATH` in scraper script

2. **API Key Errors**
   - Verify environment variables are set correctly
   - Check API key validity and quotas

3. **Vector Store Loading Failures**
   - Ensure all required files exist (`olifan_faiss.index`, `olifan_index_mapping.pkl`)
   - Check file permissions

4. **CORS Issues**
   - Verify frontend and backend ports match CORS settings
   - Update `allow_origins` in backend if using different ports

### Debugging Commands

```bash
# Test backend health
curl http://localhost:8000/health

# Test chat endpoint
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Test message"}'

# Check indexed sources
curl "http://localhost:8000/sources?query=test&limit=3"
```

## Maintenance

### Regular Updates
1. Re-run scraper periodically to keep content fresh
2. Rebuild vector store after scraping
3. Monitor API usage and costs
4. Update dependencies regularly

### Monitoring
- Check API logs for errors
- Monitor response times
- Track token usage for cost management
- Verify data freshness

## Future Enhancements

- [ ] Add admin dashboard for content management
- [ ] Implement user authentication
- [ ] Add analytics and usage tracking
- [ ] Support for multiple languages
- [ ] Enhanced document processing (PDF, DOCX)
- [ ] Real-time content updates
- [ ] Advanced conversation analytics

## License
This project is proprietary to Olifan Group.