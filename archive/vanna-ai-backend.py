import os
import vanna
from vanna.remote import VannaDefault
from google.cloud import bigquery
from google.oauth2 import service_account
from sentence_transformers import SentenceTransformer
import numpy as np
import chromadb
import json
from typing import Dict, List, Optional, Tuple

class SQLAgent:
    def __init__(self, vanna_api_key: str, bigquery_credentials_path: str, 
                 vector_db_path: str = "./vector_db"):
        """
        Initialize the SQL Agent with Vanna AI, BigQuery, and Vector Database
        
        Args:
            vanna_api_key: API key for Vanna AI
            bigquery_credentials_path: Path to BigQuery service account JSON
            vector_db_path: Path to store the vector database
        """
        # Initialize Vanna AI
        self.vn = VannaDefault(api_key=vanna_api_key)
        
        # Initialize BigQuery client
        credentials = service_account.Credentials.from_service_account_file(
            bigquery_credentials_path, scopes=["https://www.googleapis.com/auth/bigquery"]
        )
        self.bq_client = bigquery.Client(credentials=credentials, project=credentials.project_id)
        
        # Initialize Vector Database
        self.client = chromadb.PersistentClient(path=vector_db_path)
        self.collection = self.client.get_or_create_collection(
            name="sql_question_pairs",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Initialize Sentence Transformer for embeddings
        self.model = SentenceTransformer('all-MiniLM-L6-v2')  # Lightweight model good for semantic similarity
        
    def connect_to_bigquery_schema(self, dataset_id: str):
        """
        Connect Vanna AI to BigQuery schema for better SQL generation
        
        Args:
            dataset_id: BigQuery dataset ID to extract schema from
        """
        # Get all tables in the dataset
        tables = list(self.bq_client.list_tables(dataset_id))
        
        ddl_statements = []
        for table in tables:
            table_ref = self.bq_client.dataset(dataset_id).table(table.table_id)
            table_obj = self.bq_client.get_table(table_ref)
            
            # Create DDL for each table
            ddl = f"CREATE TABLE {dataset_id}.{table.table_id} (\n"
            columns = []
            for field in table_obj.schema:
                column_type = field.field_type
                nullable = "NULL" if field.mode == "NULLABLE" else "NOT NULL"
                columns.append(f"  {field.name} {column_type} {nullable}")
            ddl += ",\n".join(columns)
            ddl += "\n);"
            ddl_statements.append(ddl)
        
        # Train Vanna on the schema
        self.vn.train(ddl="\n\n".join(ddl_statements))
        print(f"Trained Vanna AI on {len(tables)} tables from {dataset_id}")
        
    def store_query_pair(self, question: str, sql: str, execution_time: float, 
                        was_successful: bool, result_preview: Optional[str] = None):
        """
        Store a question-SQL pair in the vector database
        
        Args:
            question: The natural language question
            sql: The generated SQL query
            execution_time: Time taken to execute the query (in seconds)
            was_successful: Whether the query executed successfully
            result_preview: Optional preview of the results
        """
        # Generate embedding for the question
        embedding = self.model.encode(question).tolist()
        
        # Store the pair with metadata
        metadata = {
            "sql": sql,
            "execution_time": execution_time,
            "was_successful": was_successful,
            "timestamp": str(pd.Timestamp.now()),
        }
        
        if result_preview:
            metadata["result_preview"] = result_preview
            
        # Generate a unique ID
        import hashlib
        id = hashlib.md5(question.encode()).hexdigest()
        
        # Upsert to collection
        self.collection.upsert(
            ids=[id],
            embeddings=[embedding],
            documents=[question],
            metadatas=[metadata]
        )
        
    def find_similar_queries(self, question: str, top_k: int = 3) -> List[Dict]:
        """
        Find similar queries to the input question
        
        Args:
            question: The natural language question
            top_k: Number of similar queries to return
        
        Returns:
            List of similar query pairs with their metadata
        """
        # Generate embedding for the question
        embedding = self.model.encode(question).tolist()
        
        # Query the collection
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k
        )
        
        similar_queries = []
        if results and len(results['ids'][0]) > 0:
            for i in range(len(results['ids'][0])):
                similar_queries.append({
                    "question": results['documents'][0][i],
                    "sql": results['metadatas'][0][i]['sql'],
                    "was_successful": results['metadatas'][0][i]['was_successful'],
                    "execution_time": results['metadatas'][0][i]['execution_time'],
                })
        
        return similar_queries
    
    def generate_sql(self, question: str) -> Tuple[str, List[Dict]]:
        """
        Generate SQL from a natural language question, with help from similar queries
        
        Args:
            question: The natural language question
        
        Returns:
            Generated SQL query and list of similar queries used for reference
        """
        # Find similar queries
        similar_queries = self.find_similar_queries(question)
        
        # If we have similar successful queries, use them as examples for Vanna
        example_pairs = []
        for query in similar_queries:
            if query["was_successful"]:
                example_pairs.append({
                    "question": query["question"],
                    "sql": query["sql"]
                })
        
        # Generate SQL with Vanna AI, potentially using examples
        if example_pairs:
            # Add examples to improve generation
            sql = self.vn.generate_sql(question=question, examples=example_pairs)
        else:
            # Generate without examples
            sql = self.vn.generate_sql(question=question)
            
        return sql, similar_queries
    
    def execute_query(self, sql: str) -> Tuple[bigquery.table.RowIterator, float]:
        """
        Execute a SQL query on BigQuery and measure execution time
        
        Args:
            sql: SQL query to execute
        
        Returns:
            Query results and execution time
        """
        import time
        start_time = time.time()
        
        # Execute the query
        query_job = self.bq_client.query(sql)
        results = query_job.result()
        
        execution_time = time.time() - start_time
        
        return results, execution_time
    
    def query(self, question: str, store_results: bool = True, 
             require_approval: bool = True, approved: bool = False) -> Dict:
        """
        Main method to process a natural language question
        
        Args:
            question: Natural language question
            store_results: Whether to store the question-SQL pair
            require_approval: Whether to require user approval before execution
            approved: Whether the SQL has been approved by the user
        
        Returns:
            Dictionary with results and metadata
        """
        # Generate SQL
        sql, similar_queries = self.generate_sql(question)
        
        # If approval is required but not yet provided, return early with just the SQL
        if require_approval and not approved:
            return {
                "question": question,
                "sql": sql,
                "requires_approval": True,
                "was_successful": None,
                "execution_time": 0,
                "similar_queries": similar_queries,
                "awaiting_approval": True
            }
        
        # If we reach here, either approval isn't required or it's been granted
        try:
            # Execute the query
            results, execution_time = self.execute_query(sql)
            
            # Convert to DataFrame for easier manipulation
            import pandas as pd
            df = results.to_dataframe()
            
            # Get a preview as string
            result_preview = df.head(5).to_string() if not df.empty else "No results"
            
            was_successful = True
            error_message = None
            
        except Exception as e:
            was_successful = False
            error_message = str(e)
            execution_time = 0
            df = None
            result_preview = None
        
        # Store the query pair if requested
        if store_results:
            self.store_query_pair(
                question=question,
                sql=sql,
                execution_time=execution_time,
                was_successful=was_successful,
                result_preview=result_preview
            )
        
        # Prepare response
        response = {
            "question": question,
            "sql": sql,
            "was_successful": was_successful,
            "execution_time": execution_time,
            "similar_queries": similar_queries,
            "requires_approval": require_approval,
            "approved": approved
        }
        
        if was_successful:
            response["results"] = df
            response["result_preview"] = result_preview
        else:
            response["error_message"] = error_message
            
        return response
    
    def get_query_history(self, limit: int = 10) -> List[Dict]:
        """
        Get history of stored queries
        
        Args:
            limit: Maximum number of queries to return
        
        Returns:
            List of query pairs with metadata
        """
        # Get all items from the collection
        results = self.collection.get(limit=limit)
        
        history = []
        if results and len(results['ids']) > 0:
            for i in range(len(results['ids'])):
                history.append({
                    "question": results['documents'][i],
                    "sql": results['metadatas'][i]['sql'],
                    "was_successful": results['metadatas'][i]['was_successful'],
                    "execution_time": results['metadatas'][i]['execution_time'],
                    "timestamp": results['metadatas'][i]['timestamp']
                })
        
        return history

# Example usage
if __name__ == "__main__":
    # Initialize the agent
    agent = SQLAgent(
        vanna_api_key="your_vanna_api_key",
        bigquery_credentials_path="path/to/your/bigquery_credentials.json",
        vector_db_path="./vector_db"
    )
    
    # Connect to BigQuery schema
    agent.connect_to_bigquery_schema("your_dataset_id")
    
    # Example query
    result = agent.query("Show me total sales by region for the last quarter")
    
    # Print the result
    if result["was_successful"]:
        print(f"Generated SQL: {result['sql']}")
        print(f"Execution time: {result['execution_time']:.2f} seconds")
        print("\nResult preview:")
        print(result["result_preview"])
    else:
        print(f"Query failed: {result['error_message']}")