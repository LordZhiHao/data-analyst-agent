#!/usr/bin/env python3
"""
Vanna AI Setup with Gemini, BigQuery and MongoDB Vector Store for Grocery Dataset
--------------------------------------------------------------------------------
This script sets up Vanna AI for the Grocery dataset, using BigQuery as the
primary database and connecting to MongoDB collection with vector index creation.
Uses LangChain's GoogleGenerativeAIEmbeddings for embedding-001 model.
Updated for compatibility with Vanna 0.7.9.
"""

import os
import json
import pandas as pd
import numpy as np
import time
import importlib.util
from typing import Dict, Any, List, Optional, Union, Tuple

# Load configuration from config.json
def load_config():
    """Load configuration from config.json and set environment variables."""
    try:
        # Get the directory where the script is located
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "config.json")
        
        # Check if config.json exists
        if not os.path.exists(config_path):
            print(f"Warning: config.json not found at {config_path}")
            print("Environment variables will be loaded from system environment if available.")
            return False
            
        # Load configuration from file
        with open(config_path, 'r') as config_file:
            config = json.load(config_file)
            
        # Set environment variables
        for key, value in config.items():
            os.environ[key] = str(value)
            
        print(f"✓ Configuration loaded from {config_path}")
        return True
        
    except Exception as e:
        print(f"Error loading configuration: {e}")
        print("Environment variables will be loaded from system environment if available.")
        return False

# Load configuration at import time
load_config()

# Import Vanna - updated for version 0.7.9
import vanna
from vanna.remote import VannaDefault

# Import database connectors
from pymongo import MongoClient
from google.cloud import bigquery
from google.oauth2 import service_account

from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings

class VannaGrocerySetup:
    """
    Setup class for Vanna AI with the Grocery dataset. Uses BigQuery as primary database
    and connects to MongoDB collection with LangChain embedding integration.
    """
    
    def __init__(self, 
                 google_api_key: Optional[str] = None,
                 service_account_path: Optional[str] = None,
                 mongo_connection_string: Optional[str] = None,
                 mongo_db_name: Optional[str] = None,
                 mongo_collection_name: Optional[str] = None,
                 create_vector_index: bool = True,
                 vector_dimension: int = 768,  # dimension for embedding-001
                 bigquery_project_id: Optional[str] = None,
                 bigquery_dataset_id: Optional[str] = "sqlAgentTestv1"):
        """
        Initialize the VannaGrocerySetup class.
        
        Args:
            google_api_key: API key for Google Gemini
            service_account_path: Path to GCP service account key file
            mongo_connection_string: MongoDB connection string 
            mongo_db_name: MongoDB database name
            mongo_collection_name: MongoDB collection name for vector storage
            create_vector_index: Whether to create a vector index on the collection
            vector_dimension: Dimension of the vector embeddings (768 for embedding-001)
            bigquery_project_id: Google Cloud project ID for BigQuery
            bigquery_dataset_id: The dataset ID in BigQuery (default: sqlAgentTestv1)
        """
        # Use environment variables if parameters not provided
        self.google_api_key = google_api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        self.service_account_path = service_account_path or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        self.mongo_connection_string = mongo_connection_string or os.environ.get("MONGO_CONNECTION_STRING")
        self.mongo_db_name = mongo_db_name or os.environ.get("MONGO_DB_NAME")
        self.mongo_collection_name = mongo_collection_name or os.environ.get("MONGO_COLLECTION_NAME")
        self.create_vector_index = create_vector_index
        self.vector_dimension = vector_dimension
        self.bigquery_project_id = bigquery_project_id or os.environ.get("BIGQUERY_PROJECT_ID")
        self.bigquery_dataset_id = bigquery_dataset_id
        
        # Initialize components as None
        self.vanna = None
        self.mongo_client = None
        self.mongo_db = None
        self.vector_collection = None
        self.bigquery_client = None
        self.embedding_model = None
        
        # Check for required credentials
        self._check_credentials()
        
    def _check_credentials(self):
        """Verify that necessary credentials are available."""
        missing = []
        
        if not self.google_api_key:
            missing.append("Google API Key or GEMINI_API_KEY")
            
        if not self.mongo_connection_string:
            missing.append("MongoDB Connection String")
            
        if not self.mongo_db_name:
            missing.append("MongoDB Database Name")
            
        if not self.mongo_collection_name:
            missing.append("MongoDB Collection Name")
            
        if not self.bigquery_project_id:
            missing.append("BigQuery Project ID")
            
        if missing:
            print(f"Warning: The following credentials are missing: {', '.join(missing)}")
            print("Some functionality may be limited until these are provided.")
    
    def _install_required_packages(self):
        """Install required packages if not already installed."""
        required_packages = [
            "langchain_google_genai",
            "langchain_mongodb"
        ]
        
        for package in required_packages:
            if importlib.util.find_spec(package) is None:
                print(f"Installing required package: {package}")
                import subprocess
                subprocess.check_call(["pip", "install", package], 
                                     stdout=subprocess.DEVNULL, 
                                     stderr=subprocess.DEVNULL)
    
    def setup_vanna(self, model: str = "gemini-2.5-flash"):
        """
        Set up Vanna with Gemini model.
        
        Args:
            model: Gemini model to use (default: gemini-2.5-flash)
            
        Returns:
            The Vanna instance
        """
        if not self.google_api_key:
            raise ValueError("Google API key is required to set up Vanna with Gemini")
        
        # Initialize Vanna with Gemini model - updated for Vanna 0.7.9
        self.vanna = VannaDefault(
            model=model,
            api_key=self.google_api_key
        )
        
        print(f"✓ Vanna AI initialized with model: {model}")
        return self.vanna
    
    def connect_to_mongodb_collection(self):
        """
        Connect to MongoDB collection for vector storage and create vector index if needed.
        
        Returns:
            The MongoDB collection for vector storage
        """
        if not self.mongo_connection_string or not self.mongo_db_name or not self.mongo_collection_name:
            raise ValueError("MongoDB connection string, database name, and collection name are required")
        
        # Connect to MongoDB
        self.mongo_client = MongoClient(self.mongo_connection_string)
        self.mongo_db = self.mongo_client[self.mongo_db_name]
        
        # Connect to the collection (will create if it doesn't exist)
        self.vector_collection = self.mongo_db[self.mongo_collection_name]
        
        # Check if the collection exists and has documents
        doc_count = self.vector_collection.count_documents({})
        print(f"✓ Connected to MongoDB collection: {self.mongo_db_name}.{self.mongo_collection_name}")
        print(f"  Collection contains {doc_count} documents")
        
        # Check for vector index and create if requested
        self._setup_vector_index()
        
        return self.vector_collection
    
    def _setup_vector_index(self):
        """Create or verify vector index on the MongoDB collection."""
        try:
            # Check if the index already exists
            existing_indexes = self.vector_collection.index_information()
            has_vector_index = any("vector" in idx_name for idx_name in existing_indexes)
            
            if has_vector_index:
                print("✓ Vector search index already exists on collection")
                return
            
            # If no vector index exists and we're asked to create one
            if self.create_vector_index:
                # Create a sample document if collection is empty to enable index creation
                doc_count = self.vector_collection.count_documents({})
                if doc_count == 0:
                    print("  Collection is empty, creating a sample document to enable index creation...")
                    sample_embedding = [0.0] * self.vector_dimension  # Create a zero vector
                    self.vector_collection.insert_one({
                        "text": "Sample document for index creation",
                        "embedding": sample_embedding,
                        "metadata": {"type": "sample"},
                        "created_at": pd.Timestamp.now().isoformat()
                    })
                
                # For MongoDB Atlas (using Atlas UI automatically)
                print("Creating vector search index on MongoDB collection...")
                print("This operation will create a vector search index in one of two ways:")
                
                # Try to create a vector search index directly (MongoDB 7.0+)
                try:
                    # Method 1: Try to create using MongoDB 7.0+ native vector search
                    index_model = {
                        "name": "vector_index",
                        "key": [("embedding", "vector")],
                        "vectorOptions": {
                            "dimensions": self.vector_dimension,
                            "similarity": "cosine" 
                        }
                    }
                    self.vector_collection.create_index([("embedding", "vector")], 
                                               name="vector_index",
                                               vectorOptions={"dimensions": self.vector_dimension})
                    print("✓ Successfully created native vector search index")
                except Exception as native_error:
                    print(f"  Native vector index creation failed: {native_error}")
                    
                    # Method 2: Try to create using Atlas Search (if MongoDB Atlas)
                    try:
                        # Atlas search index creation via command
                        self.mongo_db.command({
                            "createSearchIndex": self.mongo_collection_name,
                            "name": "vector_index",
                            "definition": {
                                "mappings": {
                                    "dynamic": True,
                                    "fields": {
                                        "embedding": {
                                            "type": "vector",
                                            "dimensions": self.vector_dimension,
                                            "similarity": "cosine"
                                        }
                                    }
                                }
                            }
                        })
                        print("✓ Successfully created Atlas Search vector index")
                    except Exception as atlas_error:
                        print(f"  Atlas Search index creation failed: {atlas_error}")
                        print("\n  IMPORTANT: If using MongoDB Atlas, you'll need to create the vector index manually:")
                        print("  1. Go to the Atlas UI > Database > Search tab")
                        print(f"  2. Create a new index on collection '{self.mongo_collection_name}'")
                        print("  3. Use JSON editor and paste this configuration:")
                        print(f"""
                        {{
                          "mappings": {{
                            "dynamic": true,
                            "fields": {{
                              "embedding": {{
                                "dimensions": {self.vector_dimension},
                                "similarity": "cosine",
                                "type": "vector"
                              }}
                            }}
                          }}
                        }}
                        """)
                        print("  4. Create the index and wait for it to finish building\n")
            else:
                print("Note: Vector index creation is disabled. If you need vector search functionality,")
                print("enable index creation or create the index manually in the MongoDB Atlas UI.")
                
        except Exception as e:
            print(f"Warning: Error checking/creating vector index: {e}")
            print("You may need to create the vector index manually in MongoDB Atlas.")
    
    def connect_bigquery(self):
        """
        Connect to BigQuery as the primary SQL database.
        
        Returns:
            The BigQuery client
        """
        if not self.bigquery_project_id:
            raise ValueError("BigQuery project ID is required")
        
        if self.vanna is None:
            raise ValueError("Vanna must be set up first. Call setup_vanna() before connecting databases.")
        
        # Set up BigQuery client
        if self.service_account_path:
            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_path
            )
            self.bigquery_client = bigquery.Client(
                project=self.bigquery_project_id,
                credentials=credentials
            )
            
            # Connect Vanna to BigQuery - updated for Vanna 0.7.9
            self.vanna.connect_to_bigquery(
                project_id=self.bigquery_project_id,
                credentials_path=self.service_account_path
            )
        else:
            # Use application default credentials
            self.bigquery_client = bigquery.Client(project=self.bigquery_project_id)
            
            # Connect Vanna to BigQuery with default credentials - updated for Vanna 0.7.9
            self.vanna.connect_to_database(
                "bigquery",
                project_id=self.bigquery_project_id
            )
        
        print(f"✓ Connected to BigQuery project: {self.bigquery_project_id}")
        return self.bigquery_client
    
    def _setup_embedding_model(self):
        """
        Set up LangChain GoogleGenerativeAIEmbeddings model (embedding-001).
        """
        # Install required packages if not already installed
        self._install_required_packages()
        
        # Initialize the embedding model
        self.embedding_model = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=self.google_api_key
        )
        
        print("✓ Initialized LangChain GoogleGenerativeAIEmbeddings (embedding-001 model)")
    
    def generate_embeddings(self, text: str) -> np.ndarray:
        """
        Generate embeddings for text using LangChain's GoogleGenerativeAIEmbeddings.
        
        Args:
            text: The text to generate embeddings for
            
        Returns:
            Numpy array of embedding values with dimension 768
        """
        if self.vanna is None:
            raise ValueError("Vanna must be set up first")
            
        try:
            # Initialize the embedding model if not already done
            if self.embedding_model is None:
                self._setup_embedding_model()
        
            # Generate embeddings using LangChain's embedding model
            embedding = self.embedding_model.embed_query(text)
            
            # Convert to numpy array
            return np.array(embedding)
                
        except Exception as e:
            print(f"Error generating embeddings with LangChain: {e}")
            print("Falling back to Vanna's default embedding method")
            
            # Fall back to Vanna's default embedding method - updated for Vanna 0.7.9
            try:
                embedding = self.vanna.generate_embeddings(text)
                return np.array(embedding)
            except:
                # If that fails too, just return a random embedding
                print("Warning: Using random embedding as fallback")
                return np.random.rand(self.vector_dimension)
    
    def train_on_documentation(self, documentation_text: str):
        """
        Train Vanna on documentation text without storing in vector database.
        
        Args:
            documentation_text: String containing documentation
        """
        if self.vanna is None:
            raise ValueError("Vanna must be set up first")
        
        # Train Vanna on the documentation - updated for Vanna 0.7.9
        self.vanna.train(documentation=documentation_text)
        
        print("✓ Trained on documentation (without vector storage)")
    
    def train_on_ddl(self, ddl_content: str):
        """
        Train Vanna on DDL as documentation without storing in vector database.
        
        Args:
            ddl_content: String containing DDL statements
        """
        if self.vanna is None:
            raise ValueError("Vanna must be set up first")
        
        # Format DDL as documentation
        ddl_doc = f"# Database Schema Definition\n\n```sql\n{ddl_content}\n```"
        
        # Train Vanna on the DDL documentation - updated for Vanna 0.7.9
        self.vanna.train(documentation=ddl_doc)
        
        print("✓ Trained on DDL as schema documentation (without vector storage)")
    
    def train_on_bigquery_schema(self):
        """
        Train Vanna on BigQuery schema using improved method that explicitly references the dataset.
        """
        if self.vanna is None or self.bigquery_client is None:
            raise ValueError("Vanna and BigQuery must be set up first")
        
        dataset_id = self.bigquery_dataset_id
        
        # Get all tables in the dataset
        dataset_ref = self.bigquery_client.dataset(dataset_id)
        
        try:
            tables = list(self.bigquery_client.list_tables(dataset_ref))
            
            # Add a header comment to identify the dataset
            ddl_statements = [f"-- Schema for dataset: {dataset_id}"]
            
            for table in tables:
                table_ref = self.bigquery_client.get_table(table.reference)
                
                # Create DDL for each table
                ddl = f"CREATE TABLE {dataset_id}.{table.table_id} (\n"
                columns = []
                for field in table_ref.schema:
                    column_type = field.field_type
                    nullable = "NULL" if field.mode == "NULLABLE" else "NOT NULL"
                    columns.append(f"  {field.name} {column_type} {nullable}")
                ddl += ",\n".join(columns)
                ddl += "\n);"
                ddl_statements.append(ddl)
                
                # Store table schema in vector DB for retrieval
                schema_text = f"Table: {table.table_id}\nSchema: {[field.name + ' (' + field.field_type + ')' for field in table_ref.schema]}"
                self.store_embedding(
                    text=schema_text,
                    metadata={
                        "type": "schema",
                        "dataset_id": dataset_id,
                        "table_id": table.table_id
                    },
                    doc_id=f"schema_{dataset_id}_{table.table_id}"
                )
            
            # Create comprehensive documentation about the dataset
            documentation = f"""# BigQuery Dataset: {dataset_id}

This schema represents the BigQuery dataset `{dataset_id}` containing {len(tables)} tables.
The DDL statements below define the structure of each table in this dataset.

```sql
{"\n\n".join(ddl_statements)}
```
"""
            
            # Train Vanna on both the raw DDL and as documentation - updated for Vanna 0.7.9
            self.vanna.train(sql="\n\n".join(ddl_statements))
            self.vanna.train(documentation=documentation)
            
            print(f"✓ Trained on BigQuery schema for dataset: '{dataset_id}'")
            print(f"✓ Stored schema information in vector database for {len(tables)} tables/views")
            
        except Exception as e:
            print(f"Error training on schema: {e}")
    
    def train_on_example_queries(self, example_queries: List[Dict[str, str]]):
        """
        Train Vanna on example SQL queries using Vanna AI's native convention.
        
        Args:
            example_queries: List of dictionaries with 'question' and 'sql' keys
        """
        if self.vanna is None:
            raise ValueError("Vanna must be set up first")
        
        for idx, ex in enumerate(example_queries):
            # Train Vanna on the SQL using Vanna's convention - updated for Vanna 0.7.9
            self.vanna.train(
                sql=ex['sql'],
                question=ex['question']  # Changed from 'description' to 'question' for Vanna 0.7.9
            )
        
        print(f"✓ Trained on {len(example_queries)} example queries using Vanna's convention")
    
    def store_embedding(self, 
                       text: str, 
                       metadata: Dict[str, Any] = None,
                       doc_id: str = None,
                       overwrite: bool = False) -> str:
        """
        Generate and store an embedding in MongoDB.
        
        Args:
            text: The text to generate embeddings for
            metadata: Additional metadata to store with the embedding
            doc_id: Optional document ID to use
            overwrite: Whether to overwrite existing documents with the same ID
            
        Returns:
            The ID of the stored embedding
        """
        if self.vector_collection is None:
            raise ValueError("MongoDB collection must be connected first")
            
        # Generate the embedding
        embedding = self.generate_embeddings(text).tolist()
        
        # Prepare the document
        doc = {
            "text": text,
            "embedding": embedding,
            "metadata": metadata or {},
            "created_at": pd.Timestamp.now().isoformat()
        }
        
        if doc_id:
            doc["_id"] = doc_id
            
            # Handle overwrite logic
            if overwrite:
                self.vector_collection.replace_one({"_id": doc_id}, doc, upsert=True)
            else:
                # Only insert if it doesn't exist
                result = self.vector_collection.update_one(
                    {"_id": doc_id}, 
                    {"$setOnInsert": doc}, 
                    upsert=True
                )
                
                if result.matched_count > 0 and not overwrite:
                    print(f"Document with ID {doc_id} already exists and was not overwritten")
                    return doc_id
        else:
            # Insert new document
            result = self.vector_collection.insert_one(doc)
            doc_id = str(result.inserted_id)
        
        return doc_id
    
    def find_similar_texts(self, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find similar texts using vector similarity search.
        
        Args:
            query_text: The query text
            limit: Number of similar documents to return
            
        Returns:
            List of similar documents with their similarity scores
        """
        if self.vector_collection is None:
            raise ValueError("MongoDB collection must be connected first")
            
        # Generate query embedding
        query_embedding = self.generate_embeddings(query_text).tolist()
        
        # Perform vector search (MongoDB Atlas required)
        try:
            # Try MongoDB Atlas vector search first
            results = self.vector_collection.aggregate([
                {
                    "$vectorSearch": {
                        "index": "vector_index",
                        "path": "embedding",
                        "queryVector": query_embedding,
                        "numCandidates": limit * 10,  # Search among more candidates for better results
                        "limit": limit
                    }
                },
                {
                    "$project": {
                        "_id": 1,
                        "text": 1,
                        "metadata": 1,
                        "created_at": 1,
                        "score": {"$meta": "vectorSearchScore"}
                    }
                }
            ])
            
            return list(results)
        except Exception as atlas_error:
            print(f"Atlas vector search error: {atlas_error}")
            
            try:
                # Try MongoDB 7.0+ native vector search
                results = self.vector_collection.aggregate([
                    {
                        "$search": {
                            "index": "vector_index",
                            "vectorSearch": {
                                "path": "embedding",
                                "queryVector": query_embedding,
                                "numCandidates": limit * 10,
                                "limit": limit
                            }
                        }
                    },
                    {
                        "$project": {
                            "_id": 1,
                            "text": 1,
                            "metadata": 1,
                            "created_at": 1,
                            "score": {"$meta": "searchScore"}
                        }
                    }
                ])
                
                return list(results)
            except Exception as native_error:
                print(f"Native vector search error: {native_error}")
                print("Falling back to standard embedding similarity search")
                
                # Fallback to standard embedding similarity search
                all_docs = list(self.vector_collection.find({}))
                
                # Calculate cosine similarity
                similarities = []
                for doc in all_docs:
                    doc_embedding = doc.get("embedding", [])
                    if doc_embedding:
                        similarity = np.dot(query_embedding, doc_embedding) / (
                            np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
                        )
                        similarities.append((doc, similarity))
                
                # Sort by similarity score (descending)
                similarities.sort(key=lambda x: x[1], reverse=True)
                
                # Format results similar to vector search output
                results = []
                for doc, score in similarities[:limit]:
                    doc["score"] = score
                    results.append(doc)
                    
                return results
    
    def improve_query_with_vector_search(self, question: str) -> str:
        """
        Improve a natural language query by retrieving similar examples from the vector database.
        
        Args:
            question: The natural language question
            
        Returns:
            The improved SQL query
        """
        if self.vector_collection is None or self.vanna is None:
            raise ValueError("Vector database and Vanna must be set up first")
        
        # Find similar examples
        similar_docs = self.find_similar_texts(question, limit=3)
        
        if not similar_docs:
            # If no similar examples found, just use Vanna directly - updated for Vanna 0.7.9
            return self.vanna.generate_sql(question=question)
        
        # Create a context from similar documents
        context = "Based on similar questions, here are some examples:\n\n"
        for doc in similar_docs:
            context += f"{doc['text']}\n\n"
        
        # Generate SQL with context - updated for Vanna 0.7.9
        improved_prompt = f"""
        I want to answer this question about grocery store customer data: {question}
        
        Here are some similar examples for reference:
        {context}
        
        Generate a SQL query for BigQuery that answers the original question.
        Use dataset.table format like `{self.bigquery_dataset_id}.groceries` instead of 'sqlAgentTestv1.groceries'.
        """
        
        return self.vanna.generate_sql(question=improved_prompt)
    
    def ask_with_vector_enhancement(self, question: str) -> Tuple[pd.DataFrame, str]:
        """
        Ask a question with vector database enhancement for better results.
        
        Args:
            question: The natural language question
            
        Returns:
            A tuple of (result DataFrame, generated SQL query)
        """
        # Get improved SQL using vector search
        sql = self.improve_query_with_vector_search(question)
        
        # Execute the SQL - updated for Vanna 0.7.9
        result = self.vanna.run_sql(sql=sql)
        
        return result, sql
    
    def setup_from_files(self, 
                        ddl_content: str,
                        documentation_content: str,
                        examples_content: str,
                        model: str = "gemini-2.5-flash"):
        """
        Set up Vanna AI using provided file contents.
        
        Args:
            ddl_content: String containing DDL statements (for training only, not execution)
            documentation_content: String containing documentation
            examples_content: String containing example queries in JSON format
            model: Gemini model to use
            
        Returns:
            The configured VannaGrocerySetup instance
        """
        # Step 1: Set up Vanna with Gemini
        self.setup_vanna(model=model)
        
        # Step 2: Connect to databases
        try:
            self.connect_to_mongodb_collection()
        except Exception as e:
            print(f"Warning: Could not connect to MongoDB collection: {e}")
            
        try:
            self.connect_bigquery()
        except Exception as e:
            print(f"Warning: Could not connect to BigQuery: {e}")
        
        # Step 3: Train on documentation and DDL (as documentation, not creating tables)
        try:
            # Train on the main documentation (WITHOUT vector storage)
            self.train_on_documentation(documentation_content)
            
            # Train on the DDL as schema documentation (WITHOUT vector storage)
            self.train_on_ddl(ddl_content)
        except Exception as e:
            print(f"Warning: Error training on documentation: {e}")
        
        # Step 4: Train on BigQuery schema (if tables already exist)
        try:
            self.train_on_bigquery_schema()
        except Exception as e:
            print(f"Warning: Error training on schema: {e}")
        
        # Step 5: Train on example queries using Vanna's convention
        try:
            example_queries = json.loads(examples_content)
            self.train_on_example_queries(example_queries)
        except Exception as e:
            print(f"Warning: Error training on example queries: {e}")
        
        print("✓ Complete Vanna AI setup with grocery dataset finished successfully")
        return self


# Example usage
if __name__ == "__main__":
    # Configuration is already loaded at import time
    try:
        # Get the base directory of the application
        base_dir = os.path.dirname(os.path.abspath(__file__))
        print(f"Base directory: {base_dir}")

        # Ensure the contexts directory exists
        contexts_dir = os.path.join(base_dir, "contexts")
        if not os.path.exists(contexts_dir):
            os.makedirs(contexts_dir)
            print(f"Created contexts directory at: {contexts_dir}")

        # Set paths to context files using absolute paths
        documentation_path = os.path.join(contexts_dir, "documentation.txt")
        examples_path = os.path.join(contexts_dir, "examples.json")
        ddl_path = os.path.join(contexts_dir, "custom_ddl.txt")

        # Check if context files exist
        missing_files = []
        for file_path in [documentation_path, examples_path, ddl_path]:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            print(f"Warning: The following context files are missing: {', '.join(missing_files)}")
            print("Please make sure these files exist before training the model.")
            create_samples = input("Would you like to create sample placeholder files? (y/n): ")
            if create_samples.lower() == 'y':
                # Create sample files
                if not os.path.exists(documentation_path):
                    with open(documentation_path, 'w') as f:
                        f.write("# Sample Documentation\n\nThis is a placeholder documentation file.")
                if not os.path.exists(examples_path):
                    with open(examples_path, 'w') as f:
                        f.write('[{"question": "What is the average membership fee?", "sql": "SELECT AVG(membership_fee) FROM sqlAgentTestv1.customers"}]')
                if not os.path.exists(ddl_path):
                    with open(ddl_path, 'w') as f:
                        f.write("CREATE TABLE sqlAgentTestv1.customers (customer_id STRING, membership_fee FLOAT64);")
                print("Created sample placeholder files. Please update them with your actual data.")

        # Read file contents
        print("Loading context files...")
        with open(ddl_path, 'r') as f:
            ddl_content = f.read()
            
        with open(documentation_path, 'r') as f:
            documentation_content = f.read()
            
        with open(examples_path, 'r') as f:
            examples_content = f.read()
        
        print("Context files loaded successfully.")
            
        # Initialize and setup
        print("Initializing Vanna AI...")
        vanna_setup = VannaGrocerySetup(
            # Using environment variables loaded from config.json
            google_api_key=os.environ.get("GOOGLE_API_KEY"),
            service_account_path=os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
            mongo_connection_string=os.environ.get("MONGO_CONNECTION_STRING"),
            mongo_db_name=os.environ.get("MONGO_DB_NAME"),
            mongo_collection_name=os.environ.get("MONGO_COLLECTION_NAME"),
            bigquery_project_id=os.environ.get("BIGQUERY_PROJECT_ID"),
            bigquery_dataset_id=os.environ.get("BIGQUERY_DATASET_ID") or "sqlAgentTestv1",
            # Additional parameters
            create_vector_index=True,
            vector_dimension=768  # Dimension for embedding-001
        )
        
        # Set up Vanna with files
        vanna = vanna_setup.setup_from_files(
            ddl_content=ddl_content,
            documentation_content=documentation_content,
            examples_content=examples_content,
            model="gemini-2.5-flash"
        )
        
        # Example usage
        print("\nVanna AI is ready with the grocery dataset! You can now ask questions like:")
        print("- 'What is the average membership fee by tier?'")
        print("- 'Which membership tier has the highest app engagement score?'")
        print("- 'Do customers with the app spend more on average?'")
        
        # Interactive mode
        while True:
            question = input("\nEnter your question (or 'exit' to quit): ")
            if question.lower() == 'exit':
                break
                
            try:
                # Check if required packages are installed
                try:
                    import langchain_google_genai
                except ImportError:
                    print("\nInstalling required packages...")
                    import subprocess
                    subprocess.check_call(["pip", "install", "langchain-google-genai>=0.0.3"])
                    # Re-import after installation
                    import langchain_google_genai
                
                result, sql = vanna.ask_with_vector_enhancement(question)
                
                print("\nGenerated SQL:")
                print(sql)
                print("\nResults:")
                if isinstance(result, pd.DataFrame):
                    print(result.head(10))
                else:
                    print(result)
            except Exception as e:
                print(f"\nError processing question: {e}")
                print("Make sure your BigQuery dataset is properly set up and contains the expected tables.")
                print("You can try rephrasing your question or check the system logs for more details.")
        
    except Exception as e:
        print(f"Setup error: {e}")
        import traceback
        traceback.print_exc()