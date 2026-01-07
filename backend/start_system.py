# start_system.py
import subprocess
import sys
import os
import time
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = [
        ('fastapi', 'fastapi'), 
        ('uvicorn', 'uvicorn'), 
        ('faiss-cpu', 'faiss'),
        ('sentence-transformers', 'sentence_transformers'),
        ('groq', 'groq'),
        ('tavily', 'tavily')
    ]
    
    missing = []
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(package_name)
    
    # Special handling for LangChain which has complex module structure
    try:
        import langchain_core
        import langchain_community

        # Test key LangChain imports
        from langchain_core.documents import Document
        from langchain_community.vectorstores import FAISS
        from langchain_community.embeddings import SentenceTransformerEmbeddings
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError:
        missing.append('langchain-core, langchain-community, langchain-text-splitters')
    
    # Special handling for langchain-groq
    try:
        from langchain_groq import ChatGroq
    except ImportError:
        missing.append('langchain-groq')
    
    if missing:
        print("❌ Missing dependencies:")
        for pkg in missing:
            print(f"   - {pkg}")
        print("\nInstall with: pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies found")
    return True

def check_files():
    """Check if required data files exist."""
    required_files = [
        "olifan_faiss.index",
        "olifan_index_mapping.pkl"
    ]
    
    missing = []
    for file in required_files:
        if not os.path.exists(file):
            missing.append(file)
    
    if missing:
        print("❌ Missing data files:")
        for file in missing:
            print(f"   - {file}")
        print("\nPlease run data processing first:")
        print("1. python olifan_scraper.py")
        print("2. python olifan_data_processor.py")
        return False
    
    print("✅ All required data files present")
    return True

def start_backend():
    """Start the backend API server."""
    print("🚀 Starting Backend API Server...")
    print("   URL: http://localhost:8000")
    print("   Press Ctrl+C to stop\n")
    
    try:
        # Change to the correct directory
        os.chdir(Path(__file__).parent)
        
        # Start the FastAPI server
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "olifan_backend_api:app", 
            "--host", "0.0.0.0", 
            "--port", "8000",
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n🛑 Backend server stopped")
    except Exception as e:
        print(f"❌ Failed to start backend: {e}")

def run_tests():
    """Run integration tests."""
    print("🧪 Running Integration Tests...")
    
    try:
        result = subprocess.run([
            sys.executable, "integration_test.py"
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
            
    except Exception as e:
        print(f"❌ Test execution failed: {e}")

def show_help():
    """Display help information."""
    print("""
OLIFAN AI ASSISTANT - SYSTEM STARTUP

Usage: python start_system.py [command]

Commands:
  backend    - Start the backend API server only
  test       - Run integration tests
  help       - Show this help message

If no command is specified, it will:
1. Check dependencies and data files
2. Start the backend server

Environment Variables Required:
  GROQ_API_KEY      - Your Groq API key
  TAVILY_API_KEY    - Your Tavily API key

Setup Steps:
1. Set your API keys in environment variables
2. Run python olifan_scraper.py (first time only)
3. Run python olifan_data_processor.py (first time only)
4. Run python start_system.py

For frontend:
1. cd to project root
2. npm install
3. npm run dev
    """)

def main():
    """Main startup function."""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "backend":
            if check_dependencies() and check_files():
                start_backend()
            return
        elif command == "test":
            run_tests()
            return
        elif command == "help":
            show_help()
            return
        else:
            print(f"Unknown command: {command}")
            show_help()
            return
    
    # Default behavior: check and start backend
    print("🚀 OLIFAN AI ASSISTANT - SYSTEM STARTUP")
    print("=" * 50)
    
    # Check prerequisites
    if not check_dependencies():
        return
    
    if not check_files():
        return
    
    # Check API keys
    groq_key = os.environ.get("GROQ_API_KEY")
    tavily_key = os.environ.get("TAVILY_API_KEY")
    
    if not groq_key or not tavily_key:
        print("⚠️  Warning: API keys not found in environment variables")
        print("   Please set GROQ_API_KEY and TAVILY_API_KEY")
        print("   Or create a .env file based on .env.example")
        print("   Example: copy .env.example .env and add your keys")
    
    # Start backend
    start_backend()

if __name__ == "__main__":
    main()