import os
import json
import numpy as np
import pandas as pd
import pymongo
from vanna.base import VannaBase
from vanna.google import GoogleGeminiChat
from typing import List, Dict, Any, Optional
from bson.objectid import ObjectId
from google.oauth2 import service_account
from google.cloud import bigquery
import google.generativeai as genai

class MongoDBVectorStore(VannaBase):
    def __init__(self, config=None):
        # Store the config for later use
        self.config = config or {}
        
        # Set up Google embedding model
        self._setup_embedding_model()
        
        # Initialize MongoDB connection
        if config and 'mongo_connection_string' in config:
            # Connect to MongoDB
            self.client = pymongo.MongoClient(config['mongo_connection_string'])
            self.db = self.client.get_database(config.get('mongo_db_name', 'vanna'))
            
            # Get collections
            self.ddl_collection = self.db.get_collection(config.get('mongodb_ddl_collection_name', 'ddl'))
            self.docs_collection = self.db.get_collection(config.get('mongodb_docs_collection_name', 'documentation'))
            self.q_sql_collection = self.db.get_collection(config.get('mongodb_qa_collection_name', 'question_sql'))
            
            # Check if vector indexes exist, if not, provide instructions
            self._check_vector_indexes()
        else:
            raise ValueError("MongoDB connection string is required in config")
    
    def _check_vector_indexes(self):
        """Check if vector indexes exist and provide instructions if they don't"""
        # List collections that need vector indexes
        collections = {
            "ddl": self.ddl_collection,
            "documentation": self.docs_collection,
            "question_sql": self.q_sql_collection
        }
        
        for name, collection in collections.items():
            # Try to list indexes to see if vector index exists
            indexes = collection.list_indexes()
            has_vector_index = False
            
            for index in indexes:
                if "vectorSearch" in index.get("name", ""):
                    has_vector_index = True
                    print(f"✅ Vector index found for {name} collection")
                    break
            
            if not has_vector_index:
                print(f"⚠️ No vector index found for {name} collection")
                print(f"   To optimize vector search, create an index in MongoDB Atlas with this definition:")
                print(f"""
                {{
                  "fields": [
                    {{
                      "type": "vector",
                      "path": "embedding",
                      "numDimensions": 768,
                      "similarity": "cosine"
                    }}
                  ]
                }}
                """)
    
    def _setup_embedding_model(self):
        """Set up the Google embedding model"""
        api_key = self.config.get('gemini_api_key', self.config.get('google_api_key'))
        if not api_key:
            print("Warning: No Google API key found. Will use random embeddings.")
            self._use_google_embeddings = False
            return
        
        try:
            # Configure the genai library with your API key
            genai.configure(api_key=api_key)
            
            # Get the embedding model
            self.embedding_model = "models/embedding-001"
            
            # Test the embedding model
            test_embedding = self.generate_embedding("Test embedding")
            if test_embedding:
                print(f"✅ Successfully initialized Google embedding model: {self.embedding_model}")
                print(f"   Embedding dimension: {len(test_embedding)}")
                self._use_google_embeddings = True
                # Store embedding dimension for future reference
                self.embedding_dimension = len(test_embedding)
            else:
                print("❌ Failed to get embeddings from Google. Will use random embeddings.")
                self._use_google_embeddings = False
                self.embedding_dimension = 768  # Default dimension for embedding-001
                
        except Exception as e:
            print(f"❌ Error setting up Google embedding model: {e}")
            print("   Will use random embeddings as fallback.")
            self._use_google_embeddings = False
            self.embedding_dimension = 768  # Default dimension for embedding-001
    
    def add_ddl(self, ddl: str, **kwargs) -> str:
        """Add DDL to the vector database"""
        document = {
            'text': ddl,
            'embedding': self.generate_embedding(ddl),
            'metadata': kwargs
        }
        result = self.ddl_collection.insert_one(document)
        return str(result.inserted_id)
    
    def add_documentation(self, doc: str, **kwargs) -> str:
        """Add documentation to the vector database"""
        document = {
            'text': doc,
            'embedding': self.generate_embedding(doc),
            'metadata': kwargs
        }
        result = self.docs_collection.insert_one(document)
        return str(result.inserted_id)
    
    def add_question_sql(self, question: str, sql: str, **kwargs) -> str:
        """Add question-SQL pair to the vector database"""
        document = {
            'question': question,
            'sql': sql,
            'embedding': self.generate_embedding(question),
            'metadata': kwargs
        }
        result = self.q_sql_collection.insert_one(document)
        return str(result.inserted_id)
    
    def get_related_ddl(self, question: str, **kwargs) -> list:
        """Get related DDL statements based on question similarity"""
        query_embedding = self.generate_embedding(question)
        results = self._find_similar(self.ddl_collection, query_embedding, limit=kwargs.get('limit', 5))
        return [{'id': str(item['_id']), 'text': item['text']} for item in results]
    
    def get_related_documentation(self, question: str, **kwargs) -> list:
        """Get related documentation based on question similarity"""
        query_embedding = self.generate_embedding(question)
        results = self._find_similar(self.docs_collection, query_embedding, limit=kwargs.get('limit', 5))
        return [{'id': str(item['_id']), 'text': item['text']} for item in results]
    
    def get_similar_question_sql(self, question: str, **kwargs) -> list:
        """Get similar question-SQL pairs based on question similarity"""
        query_embedding = self.generate_embedding(question)
        results = self._find_similar(self.q_sql_collection, query_embedding, limit=kwargs.get('limit', 5))
        return [{'id': str(item['_id']), 'question': item['question'], 'sql': item['sql']} for item in results]
    
    def get_training_data(self, **kwargs) -> pd.DataFrame:
        """Get all training data from the database"""
        data = []
        
        # Get DDL data
        for item in self.ddl_collection.find({}):
            data.append({
                'id': str(item['_id']),
                'type': 'ddl',
                'text': item['text']
            })
        
        # Get documentation data
        for item in self.docs_collection.find({}):
            data.append({
                'id': str(item['_id']),
                'type': 'documentation',
                'text': item['text']
            })
        
        # Get question-SQL pair data
        for item in self.q_sql_collection.find({}):
            data.append({
                'id': str(item['_id']),
                'type': 'question_sql',
                'question': item.get('question', ''),
                'sql': item.get('sql', '')
            })
        
        if not data:
            return pd.DataFrame(columns=['id', 'type', 'text', 'question', 'sql'])
        
        return pd.DataFrame(data)
    
    def remove_training_data(self, id: str, **kwargs) -> bool:
        """Remove training data by ID"""
        try:
            obj_id = ObjectId(id)
            result1 = self.ddl_collection.delete_one({'_id': obj_id})
            result2 = self.docs_collection.delete_one({'_id': obj_id})
            result3 = self.q_sql_collection.delete_one({'_id': obj_id})
            
            return result1.deleted_count > 0 or result2.deleted_count > 0 or result3.deleted_count > 0
        except Exception as e:
            print(f"Error removing training data: {e}")
            return False
    
    def _find_similar(self, collection, query_embedding, limit=5):
        """Find similar documents using MongoDB Vector Search if available, fallback to in-memory"""
        try:
            # First, try to use MongoDB Vector Search
            # Use the correct Atlas vector search syntax
            vector_search_pipeline = [
                {
                    "$vectorSearch": {
                        "index": f"{collection.name}_vector_index",  # The name should match your Atlas index
                        "path": "embedding",
                        "queryVector": query_embedding,
                        "numCandidates": limit * 10,  # Get more candidates for better results
                        "limit": limit
                    }
                }
            ]
            
            # Try to use the vector search pipeline
            try:
                results = list(collection.aggregate(vector_search_pipeline))
                if results:
                    print(f"✅ Using MongoDB Vector Search for {collection.name} collection")
                    return results
            except Exception as e:
                # If the vector search fails (e.g., no index), log and fall back to in-memory
                print(f"⚠️ MongoDB Vector Search failed for {collection.name}: {e}")
                print("   Falling back to in-memory similarity search")
        except Exception as e:
            print(f"Error in vector search: {e}")
        
        # Fall back to in-memory similarity search
        print(f"Using in-memory similarity search for {collection.name} collection")
        results = []
        for doc in collection.find({}):
            if 'embedding' in doc:
                similarity = self._cosine_similarity(query_embedding, doc['embedding'])
                results.append((doc, similarity))
        
        # Sort by similarity (descending)
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Return top results
        return [item[0] for item in results[:limit]]
    
    def _cosine_similarity(self, embedding1, embedding2):
        """Calculate cosine similarity between two embeddings"""
        a = np.array(embedding1)
        b = np.array(embedding2)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    def generate_embedding(self, text):
        """Generate embedding for text using Google's embedding model"""
        if not hasattr(self, '_use_google_embeddings') or not self._use_google_embeddings:
            # Fallback to random embeddings if Google embeddings aren't available
            # Use correct dimension (768) for embedding-001 model
            return np.random.rand(768).tolist()
        
        try:
            # Generate embedding using Google's model
            result = genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="retrieval_query"
            )
            
            # Extract the embedding
            embedding = result["embedding"]
            return embedding
            
        except Exception as e:
            print(f"Error generating Google embedding: {e}")
            print("Falling back to random embedding")
            # Fallback to random embeddings with correct dimension
            return np.random.rand(768).tolist()


class MyVanna(MongoDBVectorStore, GoogleGeminiChat):
    def __init__(self, config=None):
        if config is None:
            config = {}
        
        # First, initialize the GoogleGeminiChat parent
        # Set up Google Gemini configuration
        gemini_config = {
            'api_key': config.get('gemini_api_key', config.get('google_api_key')),
            'model': config.get('gemini-2.5-flash', 'gemini-2.5-flash')
        }
        
        # Initialize GoogleGeminiChat first, which will handle the VannaBase init
        GoogleGeminiChat.__init__(self, config=gemini_config)
        
        # Then initialize the MongoDBVectorStore
        MongoDBVectorStore.__init__(self, config)
        
        # Set up tracking for run_sql initialization
        self._has_initialized_run_sql = False
    
    def connect_to_bigquery(self, project_id, dataset_id, credentials_path=None):
        """Override connect_to_bigquery to use explicit credentials"""
        if credentials_path is None:
            credentials_path = self.config.get('google_application_credentials', 
                                            './sql-agent-project.json')
        
        print(f"Using credentials file: {credentials_path}")
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(f"Credentials file not found at: {credentials_path}")
        
        try:
            # Create explicit credentials
            print("Creating explicit credentials from service account file...")
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            
            # Create client with explicit credentials
            print(f"Creating BigQuery client for project: {project_id}...")
            self.client = bigquery.Client(
                credentials=credentials,
                project=project_id,
            )
            
            # Test connection with simple query
            print("Testing connection with a simple query...")
            query_job = self.client.query("SELECT 1 as test")
            results = query_job.result()
            for row in results:
                print(f"Connection test successful! Test value: {row.test}")
            
            self.project_id = project_id
            self.dataset_id = dataset_id
            
            # Store these for later use
            self._bigquery_client = self.client
            self._bigquery_project_id = project_id
            self._bigquery_dataset_id = dataset_id
            
            # Set the run_sql method to use our BigQuery client
            self._setup_run_sql_method()
            
            print(f"Successfully connected to BigQuery project '{project_id}', dataset '{dataset_id}'")
            return self
            
        except Exception as e:
            print(f"Error connecting to BigQuery: {e}")
            print(f"Error type: {type(e).__name__}")
            raise
    
    def _setup_run_sql_method(self):
        """Setup the run_sql method to use our BigQuery client"""
        self._has_initialized_run_sql = True
        
        def run_sql_bigquery(sql):
            """Run SQL query on BigQuery"""
            try:
                # Check if we have a client
                if not hasattr(self, '_bigquery_client') or self._bigquery_client is None:
                    raise ValueError("BigQuery client not initialized. Call connect_to_bigquery first.")
                
                print(f"Executing SQL query: {sql}")
                query_job = self._bigquery_client.query(sql)
                results = query_job.result()
                
                # Convert to pandas DataFrame
                df = results.to_dataframe()
                print(f"Query executed successfully! Rows returned: {len(df)}")
                return df
            except Exception as e:
                print(f"Error executing SQL query: {e}")
                raise
        
        # Set the run_sql method
        self.run_sql = run_sql_bigquery
    
    def ask(self, question, **kwargs):
        """Override ask method to ensure run_sql is set up and execute the generated SQL"""
        try:
            # Make sure run_sql is set up
            if not hasattr(self, '_has_initialized_run_sql') or not self._has_initialized_run_sql:
                self._setup_run_sql_method()
            
            # Get the SQL generated for the question
            sql = super().generate_sql(question, **kwargs)
            print(f"Generated SQL: {sql}")
            
            # Try to run the SQL
            try:
                if sql:
                    print("Executing generated SQL...")
                    results = self.run_sql(sql)
                    print(f"SQL execution successful! Rows returned: {len(results)}")
                    
                    # Store results for reference
                    self._last_results = results
                else:
                    print("No SQL was generated.")
            except Exception as e:
                print(f"Error executing generated SQL: {e}")
            
            # Return the generated SQL as normal
            return sql
                
        except Exception as e:
            print(f"Error in ask method: {e}")
            # Still return something even on error
            return f"Error: {str(e)}"