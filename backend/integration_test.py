# integration_test.py
import requests
import json
import time
import os

def test_backend_health():
    """Test if backend API is running and healthy."""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print("✅ Backend Health Check:")
            print(f"   Status: {health_data['status']}")
            print(f"   Ready: {health_data['ready']}")
            print(f"   Components: {health_data['components']}")
            return True
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Is it running on port 8000?")
        return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_chat_endpoint():
    """Test the main chat endpoint with sample queries."""
    test_messages = [
        "Bonjour, qu'est-ce que l'ingénierie patrimoniale ?",
        "Pouvez-vous m'expliquer vos services d'investissement ?",
        "Quelles solutions proposez-vous pour la retraite ?"
    ]
    
    print("\n💬 Testing Chat Endpoint:")
    
    for i, message in enumerate(test_messages, 1):
        print(f"\nTest {i}: {message}")
        print("-" * 50)
        
        try:
            payload = {
                "message": message,
                "history": []  # Empty history for first message
            }
            
            response = requests.post(
                "http://localhost:8000/chat",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Response received ({len(data['response'])} chars)")
                print(f"   Sources: {len(data.get('sources', []))}")
                
                # Show first 200 characters of response
                preview = data['response'][:200]
                if len(data['response']) > 200:
                    preview += "..."
                print(f"   Preview: {preview}")
                
                # Show source information
                if data.get('sources'):
                    print("   Sources:")
                    for j, source in enumerate(data['sources'][:2], 1):
                        print(f"     {j}. {source.get('title', 'N/A')} - {source.get('url', 'N/A')}")
                        
            else:
                print(f"❌ API Error: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
        
        # Small delay between tests
        time.sleep(1)

def test_conversation_flow():
    """Test conversation with history preservation."""
    print("\n🔄 Testing Conversation Flow:")
    print("-" * 50)
    
    conversation = [
        {"role": "user", "content": "Bonjour, je voudrais en savoir plus sur vos services."},
        {"role": "user", "content": "Plus précisément sur l'ingénierie patrimoniale."},
        {"role": "user", "content": "Et quelles sont les démarches à suivre ?"}
    ]
    
    history = []
    
    for i, message in enumerate(conversation, 1):
        print(f"\nStep {i}: {message['content']}")
        
        try:
            payload = {
                "message": message["content"],
                "history": history.copy()
            }
            
            response = requests.post(
                "http://localhost:8000/chat",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                ai_response = data['response']
                
                print(f"✅ Assistant: {ai_response[:100]}...")
                
                # Update history
                history.append({"role": "user", "content": message["content"]})
                history.append({"role": "assistant", "content": ai_response})
                
            else:
                print(f"❌ API Error: {response.status_code}")
                break
                
        except Exception as e:
            print(f"❌ Conversation test failed: {e}")
            break

def test_sources_endpoint():
    """Test the sources inspection endpoint."""
    print("\n📚 Testing Sources Endpoint:")
    print("-" * 50)
    
    try:
        response = requests.get(
            "http://localhost:8000/sources?query=patrimoine&limit=3",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            sources = data.get('sources', [])
            
            print(f"✅ Found {len(sources)} relevant sources")
            
            for i, source in enumerate(sources, 1):
                print(f"\nSource {i}:")
                print(f"  Content: {source['content'][:150]}...")
                print(f"  Title: {source['metadata'].get('title', 'N/A')}")
                print(f"  URL: {source['metadata'].get('url', 'N/A')}")
                print(f"  Type: {source['metadata'].get('type', 'N/A')}")
        else:
            print(f"❌ Sources endpoint error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Sources test failed: {e}")

def main():
    """Run complete integration tests."""
    print("OLIFAN AI ASSISTANT - INTEGRATION TEST")
    print("=" * 60)
    
    # Check if required files exist
    required_files = [
        "olifan_faiss.index",
        "olifan_index_mapping.pkl",
        "olifan_scraped_data.json"
    ]
    
    print("📁 Checking required files:")
    missing_files = []
    for file in required_files:
        if os.path.exists(file):
            size_mb = os.path.getsize(file) / (1024 * 1024)
            print(f"  ✅ {file} ({size_mb:.2f} MB)")
        else:
            print(f"  ❌ {file} - MISSING")
            missing_files.append(file)
    
    if missing_files:
        print(f"\n⚠️  Missing files: {missing_files}")
        print("Please run the scraping and processing steps first:")
        print("1. python olifan_scraper.py")
        print("2. python olifan_data_processor.py")
        return
    
    # Test backend connectivity
    print("\n📡 Testing Backend Connectivity:")
    if not test_backend_health():
        print("\n❌ Backend tests failed. Please ensure the API is running:")
        print("python olifan_backend_api.py")
        return
    
    # Run all tests
    test_chat_endpoint()
    test_conversation_flow()
    test_sources_endpoint()
    
    print("\n" + "=" * 60)
    print("INTEGRATION TESTS COMPLETED")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Start the frontend: npm run dev")
    print("2. Visit http://localhost:3000")
    print("3. Test the chat interface!")

if __name__ == "__main__":
    main()