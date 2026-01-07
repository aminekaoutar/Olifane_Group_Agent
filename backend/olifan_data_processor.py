# olifan_data_processor.py
import json
import pickle
import faiss
import numpy as np
from typing import List
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Configuration
INPUT_JSON = "olifan_scraped_data.json"
FAISS_INDEX_FILE = "olifan_faiss.index"
MAPPING_FILE = "olifan_index_mapping.pkl"

def load_scraped_data(json_file: str) -> List[dict]:
    """Load the scraped data from JSON file."""
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"Loaded {len(data)} pages from {json_file}")
        return data
    except FileNotFoundError:
        print(f"Error: File {json_file} not found.")
        return []
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return []

def create_documents_from_data(data: List[dict]) -> List[Document]:
    """Convert scraped data into LangChain Documents."""
    documents = []
    
    for item in data:
        # Create document for main text content
        if item.get("text", "").strip():
            text_doc = Document(
                page_content=item["text"],
                metadata={
                    "url": item.get("url", ""),
                    "title": item.get("title", ""),
                    "type": "text",
                    "source": "olifan_website"
                }
            )
            documents.append(text_doc)
        
        # Create documents for image texts (OCR results)
        image_texts = item.get("image_texts", [])
        image_files = item.get("image_files", [])
        
        for i, (img_text, img_path) in enumerate(zip(image_texts, image_files)):
            if img_text.strip():
                image_doc = Document(
                    page_content=img_text,
                    metadata={
                        "url": item.get("url", ""),
                        "title": item.get("title", ""),
                        "type": "image_text",
                        "image_path": img_path,
                        "image_index": i,
                        "source": "olifan_website"
                    }
                )
                documents.append(image_doc)
    
    print(f"Created {len(documents)} documents from scraped data")
    return documents

def split_documents(documents: List[Document]) -> List[Document]:
    """Split long documents into smaller chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,  # Increased chunk size for better context
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ": ", " ", ""]
    )
    
    split_docs = splitter.split_documents(documents)
    print(f"Split into {len(split_docs)} chunks")
    return split_docs

def create_vector_store(documents: List[Document]) -> FAISS:
    """Create FAISS vector store from documents."""
    print("Initializing SentenceTransformer embeddings...")
    # Using a multilingual model that works well with French
    embeddings = SentenceTransformerEmbeddings(model_name="distiluse-base-multilingual-cased-v1")
    
    print("Creating FAISS vector store...")
    vector_store = FAISS.from_documents(documents, embeddings)
    
    return vector_store

def save_vector_store(vector_store: FAISS, index_file: str, mapping_file: str):
    """Save the FAISS index and mapping to files."""
    print(f"Saving FAISS index to {index_file}...")
    vector_store.save_local(".", "olifan_temp")
    
    # Save the raw FAISS index
    faiss.write_index(vector_store.index, index_file)
    
    # Save the docstore mapping
    with open(mapping_file, "wb") as f:
        pickle.dump((vector_store.docstore._dict, vector_store.index_to_docstore_id), f)
    
    print(f"Vector store saved successfully!")
    print(f"- Index file: {index_file}")
    print(f"- Mapping file: {mapping_file}")

def load_vector_store(index_file: str, mapping_file: str) -> FAISS:
    """Load FAISS vector store from files."""
    print("Initializing embeddings...")
    embeddings = SentenceTransformerEmbeddings(model_name="distiluse-base-multilingual-cased-v1")
    
    print(f"Loading FAISS index from {index_file}...")
    # Read the raw FAISS index
    index = faiss.read_index(index_file)
    
    print(f"Loading mapping from {mapping_file}...")
    with open(mapping_file, "rb") as f:
        docstore_data, index_to_docstore_id = pickle.load(f)
    
    # Create FAISS vector store
    from langchain_community.docstore.in_memory import InMemoryDocstore
    docstore = InMemoryDocstore(docstore_data)
    
    vector_store = FAISS(
        embedding_function=embeddings,
        index=index,
        docstore=docstore,
        index_to_docstore_id=index_to_docstore_id
    )
    
    print("Vector store loaded successfully!")
    return vector_store

def test_vector_store(vector_store: FAISS):
    """Test the vector store with sample queries."""
    test_queries = [
        "Qu'est-ce que l'ingénierie patrimoniale?",
        "Services d'investissement financier",
        "Prévoyance et retraite",
        "Expertise Olifan",
        "Solutions digitales"
    ]
    
    print("\n" + "="*50)
    print("TESTING VECTOR STORE")
    print("="*50)
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 30)
        results = vector_store.similarity_search(query, k=3)
        
        for i, doc in enumerate(results, 1):
            print(f"Result {i}:")
            print(f"  Content: {doc.page_content[:200]}...")
            print(f"  URL: {doc.metadata.get('url', 'N/A')}")
            print(f"  Type: {doc.metadata.get('type', 'N/A')}")
            print()

def main():
    """Main processing pipeline."""
    print("🚀 OLIFAN DATA PROCESSING PIPELINE")
    print("="*50)
    
    # Step 1: Load scraped data
    print("\n1. Loading scraped data...")
    data = load_scraped_data(INPUT_JSON)
    if not data:
        print("❌ No data to process. Run olifan_scraper.py first.")
        return
    
    # Step 2: Create documents
    print("\n2. Creating documents...")
    documents = create_documents_from_data(data)
    if not documents:
        print("❌ No documents created.")
        return
    
    # Step 3: Split documents
    print("\n3. Splitting documents...")
    split_docs = split_documents(documents)
    
    # Step 4: Create vector store
    print("\n4. Creating vector store...")
    vector_store = create_vector_store(split_docs)
    
    # Step 5: Save vector store
    print("\n5. Saving vector store...")
    save_vector_store(vector_store, FAISS_INDEX_FILE, MAPPING_FILE)
    
    # Step 6: Test vector store
    print("\n6. Testing vector store...")
    test_vector_store(vector_store)
    
    print("\n" + "="*50)
    print("✅ PROCESSING COMPLETE!")
    print("="*50)
    print(f"Processed {len(data)} pages")
    print(f"Created {len(documents)} documents")
    print(f"Generated {len(split_docs)} chunks")
    print(f"Saved to: {FAISS_INDEX_FILE} and {MAPPING_FILE}")

if __name__ == "__main__":
    main()