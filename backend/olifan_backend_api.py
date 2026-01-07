# olifan_backend_api.py
import os
import pickle
import faiss
import uvicorn
import base64
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging

# LangChain imports
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_core.documents import Document
from langchain_groq import ChatGroq
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage

# TTS imports
try:
    from olifan_tts_service import synthesize_text_to_speech
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("⚠️ Coqui TTS not available. Install with: pip install coqui-tts torch torchaudio")

# Queue management imports
from olifan_queue_manager import get_queue_manager, RequestStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔑 Configuration
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

if not GROQ_API_KEY or not TAVILY_API_KEY:
    print("WARNING: API keys not found in environment variables.")
    print("Please set GROQ_API_KEY and TAVILY_API_KEY environment variables.")
    print("Alternatively, create a .env file with your API keys.")
    
    # Try to load from .env file if available
    try:
        from dotenv import load_dotenv
        load_dotenv()
        GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
        TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
    except ImportError:
        print("dotenv not installed. Install with: pip install python-dotenv")

# Note: API keys are checked at runtime in the ask_olifan_agent function
# This allows the server to start even if keys aren't set initially

# File paths
FAISS_INDEX_FILE = "olifan_faiss.index"
MAPPING_FILE = "olifan_index_mapping.pkl"

# Pydantic models
class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]] = []

class ChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]] = []

# Initialize FastAPI app
app = FastAPI(
    title="Olifan Group AI Assistant API",
    description="Backend API for Olifan Group's RAG-powered chat assistant",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Next.js dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for components
vectorstore = None
llm = None
llm_with_tools = None
tavily_tool = None

def load_custom_faiss_index(faiss_path: str, docstore_path: str, embeddings) -> FAISS:
    """Load FAISS index with custom loading function."""
    if not os.path.exists(faiss_path) or not os.path.exists(docstore_path):
        raise FileNotFoundError(f"Missing required files: {faiss_path} and/or {docstore_path}")
        
    index = faiss.read_index(faiss_path)

    with open(docstore_path, "rb") as f:
        docstore_data, index_to_docstore_id = pickle.load(f)

    docstore_wrapper = InMemoryDocstore(docstore_data)

    vectorstore = FAISS(
        embeddings,
        index,
        docstore_wrapper,
        index_to_docstore_id
    )
    return vectorstore

def initialize_components():
    """Initialize all required components."""
    global vectorstore, llm, llm_with_tools, tavily_tool
    
    try:
        logger.info("Initializing components...")
        
        # 1. Embeddings
        embeddings_model = SentenceTransformerEmbeddings(
            model_name="distiluse-base-multilingual-cased-v1"
        )
        logger.info("✅ Embeddings model loaded")
        
        # 2. Vector Store
        vectorstore = load_custom_faiss_index(
            faiss_path=FAISS_INDEX_FILE,
            docstore_path=MAPPING_FILE,
            embeddings=embeddings_model
        )
        logger.info("✅ FAISS vector store loaded")
        
        # 3. LLM (Groq)
        llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model="llama-3.3-70b-versatile"  # Updated to use the latest model
        )
        logger.info("✅ Groq LLM initialized")
        
        # 4. Tool (Tavily)
        os.environ["TAVILY_API_KEY"] = TAVILY_API_KEY
        tavily_tool = TavilySearchResults(max_results=3)
        llm_with_tools = llm.bind_tools([tavily_tool])
        logger.info("✅ Tavily search tool initialized")
        
        logger.info("All components initialized successfully!")
        
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        raise

def ask_olifan_agent(query: str, chat_history: List[Dict[str, str]] = []) -> tuple[str, List[Dict]]:
    """Process query using RAG with Olifan data."""
    # Check if API keys are available
    if not GROQ_API_KEY or not TAVILY_API_KEY:
        return "Error: API keys not configured. Please contact the administrator to set up the required API keys.", []
    if not vectorstore or not llm:
        return "Service temporarily unavailable. Please try again later.", []

    # 1. Retrieval (RAG)
    docs: List[Document] = vectorstore.similarity_search(query, k=4)

    # 2. Context Formatting
    context_text = "\n".join([
        f"Content: {d.page_content} (Source: {d.metadata.get('url','N/A')})"
        for d in docs
    ])

    # 3. Collect sources for citation
    sources = []
    for doc in docs:
        sources.append({
            "content": doc.page_content[:200] + "...",
            "url": doc.metadata.get("url", ""),
            "title": doc.metadata.get("title", ""),
            "type": doc.metadata.get("type", "text")
        })

    # 4. Prompt Engineering (RAG + Tool Prompt)
    system_prompt = f"""
    You are "Olifan Assistant", an official, professional, and knowledgeable virtual agent for Olifan Group.
    You specialize in wealth management, patrimony engineering, financial investment, retirement planning, and digital solutions.
    
    Always reply in the same language used by the user (French or English). When responding in French, use polite and professional language appropriate for French business culture. Ensure formal address ("vous" instead of "tu") and proper French business etiquette.
    
    Your primary mission is to answer the user's question using the CONTEXT (Olifan Group documents) provided below.
    
    If the CONTEXT is not sufficient to answer the question, or if the question is about current events,
    general knowledge, or external topics, you MUST use your search tool (Tavily) to find relevant information.
    
    Always prioritize information from Olifan Group's official content when it's relevant.
    
    CONTEXT OLIFAN GROUP:
    ---
    {context_text}
    ---
    """

    # Build conversation messages
    messages = [SystemMessage(content=system_prompt)]
    
    # Add chat history
    for message in chat_history:
        if message["role"] == "user":
            # Ensure proper French text handling
            content = message["content"]
            messages.append(HumanMessage(content=content))
        elif message["role"] == "assistant":
            messages.append(AIMessage(content=message["content"]))
    
    # Add current query
    messages.append(HumanMessage(content=query))

    # 5. First attempt with LLM
    try:
        response: AIMessage = llm_with_tools.invoke(messages)
    except Exception as e:
        logger.error(f"LLM invocation error: {e}")
        return f"Error: {str(e)}. Please check API key configuration.", sources
    
    # 6. Tool execution if needed
    if tavily_tool and response.tool_calls:
        tool_call = response.tool_calls[0]
        
        try:
            tool_output = tavily_tool.invoke(tool_call['args'])
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return response.content if response.content else "I apologize, I couldn't process that request.", sources

        # Add tool interaction to conversation
        messages.append(response)
        messages.append(
            ToolMessage(
                tool_call_id=tool_call['id'],
                content=str(tool_output)
            )
        )
        
        # Final response with external information
        try:
            final_response: AIMessage = llm.invoke(messages)
            return final_response.content, sources
        except Exception as e:
            logger.error(f"Final LLM invocation error: {e}")
            return response.content if response.content else "I apologize, I couldn't process that request.", sources
    
    # Direct response
    return response.content if response.content else "I apologize, I couldn't generate a response.", sources

# API Routes
@app.on_event("startup")
async def startup_event():
    """Initialize components on startup."""
    try:
        initialize_components()
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        # Don't raise here to allow the server to start (will show error in health check)

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "Olifan Group AI Assistant API",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Detailed health check."""
    components_status = {
        "vectorstore": vectorstore is not None,
        "llm": llm is not None,
        "tavily_tool": tavily_tool is not None
    }
    
    overall_status = all(components_status.values())
    
    return {
        "status": "healthy" if overall_status else "degraded",
        "components": components_status,
        "ready": overall_status
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint with queue management."""
    queue_mgr = get_queue_manager()
    user_id = "anonymous"  # In production, use actual user identification
    
    try:
        if not vectorstore or not llm:
            raise HTTPException(
                status_code=503,
                detail="Service not fully initialized. Please check logs."
            )
        
        # Add request to queue
        request_data = {
            "message": request.message,
            "history": request.history
        }
        
        request_id = await queue_mgr.add_request(user_id, request_data)
        logger.info(f"Added chat request {request_id} to queue")
        
        # Wait for processing slot
        max_wait_time = 300  # 5 minutes max wait
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # Check if we can start processing
            status_info = await queue_mgr.get_request_status(request_id)
            if not status_info:
                raise HTTPException(status_code=404, detail="Request not found")
            
            status = status_info["status"]
            
            if status == RequestStatus.PROCESSING.value:
                # Our turn to process
                break
            elif status == RequestStatus.WAITING.value:
                # Still waiting in queue
                queue_position = status_info.get("queue_position")
                if queue_position:
                    logger.info(f"Request {request_id} waiting at position {queue_position}")
                
                # Check timeout
                if asyncio.get_event_loop().time() - start_time > max_wait_time:
                    await queue_mgr.cancel_request(request_id)
                    raise HTTPException(status_code=408, detail="Request timeout in queue")
                
                # Wait before checking again
                await asyncio.sleep(2)
                continue
            elif status == RequestStatus.FAILED.value:
                error_msg = status_info.get("error_message", "Unknown error")
                raise HTTPException(status_code=500, detail=f"Request failed: {error_msg}")
            elif status == RequestStatus.COMPLETED.value:
                # Already completed?
                break
            else:
                raise HTTPException(status_code=500, detail="Unexpected request status")
        
        # Process the query
        try:
            response_text, sources = ask_olifan_agent(
                query=request.message,
                chat_history=request.history
            )
            
            # Mark request as completed
            await queue_mgr.complete_request(request_id, success=True)
            
            return ChatResponse(
                response=response_text,
                sources=sources
            )
            
        except Exception as processing_error:
            # Mark request as failed
            await queue_mgr.complete_request(request_id, success=False, error_message=str(processing_error))
            raise processing_error
        
    except HTTPException:
        # Re-raise HTTP exceptions as they are
        raise
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        # Return a user-friendly error instead of 500
        return ChatResponse(
            response=f"Error: {str(e)}. Please check API key configuration.",
            sources=[]
        )

# TTS Endpoint
@app.post("/tts")
async def text_to_speech(request: dict):
    """Convert text to speech using Coqui TTS"""
    if not TTS_AVAILABLE:
        raise HTTPException(status_code=501, detail="TTS service not available. Please install coqui-tts.")
    
    text = request.get("text", "")
    language = request.get("language", "fr")
    
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    try:
        # Generate speech
        audio_bytes = synthesize_text_to_speech(text, language)
        
        # Return as base64 encoded WAV
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        return {
            "audio": audio_base64,
            "format": "wav",
            "language": language
        }
    except Exception as e:
        logger.error(f"TTS endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")

@app.get("/queue/stats")
async def get_queue_stats():
    """Get queue statistics."""
    queue_mgr = get_queue_manager()
    stats = await queue_mgr.get_queue_stats()
    return stats

@app.get("/queue/status/{request_id}")
async def get_request_status(request_id: str):
    """Get status of a specific request."""
    queue_mgr = get_queue_manager()
    status = await queue_mgr.get_request_status(request_id)
    if not status:
        raise HTTPException(status_code=404, detail="Request not found")
    return status

@app.delete("/queue/cancel/{request_id}")
async def cancel_request(request_id: str):
    """Cancel a pending request."""
    queue_mgr = get_queue_manager()
    cancelled = await queue_mgr.cancel_request(request_id)
    if not cancelled:
        raise HTTPException(status_code=400, detail="Cannot cancel request")
    return {"message": "Request cancelled successfully"}

@app.get("/sources")
async def get_sources(query: str = "", limit: int = 5):
    """Get relevant sources for a query (for debugging/testing)."""
    try:
        if not vectorstore:
            raise HTTPException(status_code=503, detail="Vector store not available")
        
        if not query:
            # Return sample documents
            docs = list(vectorstore.docstore._dict.values())[:limit]
        else:
            docs = vectorstore.similarity_search(query, k=limit)
        
        sources = []
        for doc in docs:
            sources.append({
                "content": doc.page_content[:300] + "...",
                "metadata": doc.metadata
            })
        
        return {"sources": sources}
        
    except Exception as e:
        logger.error(f"Sources endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "olifan_backend_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )