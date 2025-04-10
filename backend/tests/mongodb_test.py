# mongodb_test.py
from pymongo import MongoClient
import numpy as np
from sentence_transformers import SentenceTransformer
import sys

def test_mongodb_connection(mongo_uri, db_name="vanna_agent", collection_name="query_history"):
    """Test MongoDB connection and vector search capabilities"""
    print(f"Testing connection to: {mongo_uri}")
    
    try:
        # Connect to MongoDB
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        
        # Verify connection by getting server info
        server_info = client.server_info()
        print("✅ Connected to MongoDB successfully!")
        print(f"Server version: {server_info.get('version')}")
        
        # Check if we're using Atlas (which supports vector search)
        is_atlas = "atlas" in client.admin.command("buildInfo").get("version", "")
        if is_atlas:
            print("✅ Connected to MongoDB Atlas (vector search should be available)")
        else:
            print("ℹ️ Connected to MongoDB Community Edition (will use text search fallback)")
        
        # Get the database and collection
        db = client[db_name]
        collection = db[collection_name]
        
        # Insert a test document with embedding
        print("\nTesting document insertion with embedding...")
        
        # Create a small test embedding
        embedding = np.random.rand(384).tolist()
        
        # Insert a test document
        result = collection.insert_one({
            "question": "Test question for MongoDB connection",
            "sql": "SELECT * FROM test",
            "embedding": embedding,
            "was_successful": True,
            "execution_time": 0.1,
            "timestamp": "2023-01-01T00:00:00"
        })
        
        print(f"✅ Test document inserted with ID: {result.inserted_id}")
        
        # Test vector search if on Atlas
        if is_atlas:
            print("\nTesting vector search capability...")
            try:
                # Try a simple vector search
                pipeline = [
                    {
                        "$vectorSearch": {
                            "index": "vector_index",
                            "queryVector": embedding,
                            "numCandidates": 10,
                            "limit": 1,
                            "path": "embedding"
                        }
                    }
                ]
                
                results = list(collection.aggregate(pipeline))
                if results:
                    print("✅ Vector search is working correctly!")
                else:
                    print("⚠️ Vector search returned no results (index might not be ready yet)")
                
            except Exception as e:
                print(f"⚠️ Vector search not available: {e}")
                print("   You may need to create the vector_index in Atlas Search")
        
        # Clean up the test document
        collection.delete_one({"question": "Test question for MongoDB connection"})
        print("\n✅ Test document removed successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {e}")
        return False

if __name__ == "__main__":
    # Get connection string from command line or use default
    mongo_uri = sys.argv[1] if len(sys.argv) > 1 else "mongodb+srv://lozhihao15053:cCKcP3ioFZvB18dl@sql-agent-cluster.yb9rokx.mongodb.net/?retryWrites=true&w=majority&appName=sql-agent-cluster"
    
    # Run the test
    test_mongodb_connection(mongo_uri)