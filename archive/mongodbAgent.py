"""
SQL Agent for converting natural language to SQL using Vanna AI.
Uses MongoDB for vector storage and similarity search.
"""

import os
import time
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np
from vanna.remote import VannaDefault
from google.cloud import bigquery
from google.oauth2 import service_account
from sentence_transformers import SentenceTransformer
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

import json
import google.generativeai as genai
from dotenv import load_dotenv

class MongoDBSQLAgent:
    def __init__(self, vanna_api_key: str, bigquery_credentials_path: str, 
                mongo_uri: str, db_name: str = "vanna_agent", 
                collection_name: str = "query_history", 
                user_email: str = "lozhihao15053@gmail.com"):
        """
        Initialize the SQL Agent with Vanna AI, BigQuery, and MongoDB for vector storage
        
        Args:
            vanna_api_key: API key for Vanna AI
            bigquery_credentials_path: Path to BigQuery service account JSON
            mongo_uri: MongoDB connection URI
            db_name: MongoDB database name
            collection_name: MongoDB collection name for query history
            user_email: Email for Vanna AI authentication
        """
        # Initialize Vanna AI without email parameter
        self.vn = VannaDefault(
            model='data-analyst-agent-2', 
            api_key=vanna_api_key
        )
        
        # Try to set email separately if the method exists
        if hasattr(self.vn, 'set_email'):
            self.vn.set_email(user_email)
        
        # Initialize BigQuery client
        credentials = service_account.Credentials.from_service_account_file(
            bigquery_credentials_path, scopes=["https://www.googleapis.com/auth/bigquery"]
        )
        self.bq_client = bigquery.Client(credentials=credentials, project=credentials.project_id)

        # Set up Vanna to use our BigQuery client for SQL execution
        self._setup_vanna_run_sql()
        
        # Initialize MongoDB connection
        self.mongo_client = MongoClient(mongo_uri)
        self.db: Database = self.mongo_client[db_name]
        self.collection: Collection = self.db[collection_name]
        
        # Ensure we have a text index for simple searches and a vector index if available
        self.collection.create_index("question")
        self._setup_vector_index()
        
        # Initialize Sentence Transformer for embeddings
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def _setup_vanna_run_sql(self):
        """
        Set up Vanna to use our BigQuery client for SQL execution
        """
        def run_sql_func(sql: str):
            try:
                query_job = self.bq_client.query(sql)
                results = query_job.result()
                return results.to_dataframe()
            except Exception as e:
                print(f"Error executing SQL via Vanna: {e}")
                raise e
        
        # Tell Vanna to use our function for executing SQL
        self.vn.run_sql = run_sql_func

    def _setup_vector_index(self):
        """
        Set up vector search index if using MongoDB Atlas
        Note: Vector search requires MongoDB Atlas, not available in community edition
        """
        try:
            # Check if we're connected to Atlas with vector search capability
            is_atlas = "atlas" in self.mongo_client.admin.command("buildInfo").get("version", "")
            if is_atlas:
                # Create vector search index if it doesn't exist
                # This assumes you've enabled vector search in your Atlas cluster
                indexes = list(self.db.list_indexes())
                index_names = [idx.get("name") for idx in indexes]
                
                if "vector_index" not in index_names:
                    # Create a vector search index
                    self.db.command({
                        "createSearchIndex": self.collection.name,
                        "name": "vector_index",
                        "definition": {
                            "mappings": {
                                "dynamic": True,
                                "fields": {
                                    "embedding": {
                                        "type": "knnVector",
                                        "dimensions": 384,  # Matches the embedding model dimension
                                        "similarity": "cosine"
                                    }
                                }
                            }
                        }
                    })
                    print("Created vector search index in MongoDB Atlas")
            else:
                print("Vector search not available - using standard MongoDB")
        except Exception as e:
            print(f"Error setting up vector index: {e}")
            print("Falling back to text-based similarity")
        
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
        return f"Trained Vanna AI on {len(tables)} tables from {dataset_id}"
        
    def add_manual_context(self, context_type, content):
        """
        Add manual context to Vanna AI for improved SQL generation
        
        Args:
            context_type: Type of context ('documentation', 'examples', or 'ddl')
            content: The actual content to train Vanna with
        
        Returns:
            Result message from training
        """
        try:
            if context_type == 'documentation':
                self.vn.train(documentation=content)
                return "Added documentation context to Vanna AI"
            elif context_type == 'examples':
                # If content is a string representation of JSON, parse it
                if isinstance(content, str):
                    try:
                        examples = json.loads(content)
                        # Check if Vanna supports the examples parameter by inspecting the method signature
                        import inspect
                        train_params = inspect.signature(self.vn.train).parameters
                        
                        if 'examples' in train_params:
                            self.vn.train(examples=examples)
                            return "Added example queries to Vanna AI"
                        else:
                            # For compatibility with older Vanna versions, try adding examples one by one
                            success_count = 0
                            for example in examples:
                                if 'question' in example and 'sql' in example:
                                    try:
                                        # Some Vanna versions use 'add_question_sql' instead of 'train'
                                        if hasattr(self.vn, 'add_question_sql'):
                                            self.vn.add_question_sql(question=example['question'], sql=example['sql'])
                                        else:
                                            # Try to add directly with train using question and sql parameters
                                            self.vn.train(question=example['question'], sql=example['sql'])
                                        success_count += 1
                                    except Exception as inner_e:
                                        print(f"Error adding example {example['question']}: {str(inner_e)}")
                            
                            if success_count > 0:
                                return f"Added {success_count} example queries to Vanna AI using alternative method"
                            else:
                                return "Unable to add examples - incompatible Vanna AI version"
                    except json.JSONDecodeError:
                        raise ValueError("Examples content must be valid JSON with question-sql pairs")
                else:
                    # Same logic as above but for direct object input
                    # Check if Vanna supports the examples parameter
                    import inspect
                    train_params = inspect.signature(self.vn.train).parameters
                    
                    if 'examples' in train_params:
                        self.vn.train(examples=content)
                        return "Added example queries to Vanna AI"
                    else:
                        # Alternative approach for compatibility
                        success_count = 0
                        for example in content:
                            if 'question' in example and 'sql' in example:
                                try:
                                    if hasattr(self.vn, 'add_question_sql'):
                                        self.vn.add_question_sql(question=example['question'], sql=example['sql'])
                                    else:
                                        self.vn.train(question=example['question'], sql=example['sql'])
                                    success_count += 1
                                except Exception as inner_e:
                                    print(f"Error adding example {example['question']}: {str(inner_e)}")
                        
                        if success_count > 0:
                            return f"Added {success_count} example queries to Vanna AI using alternative method"
                        else:
                            return "Unable to add examples - incompatible Vanna AI version"
            elif context_type == 'ddl':
                self.vn.train(ddl=content)
                return "Added custom DDL to Vanna AI"
            else:
                raise ValueError("Context type must be 'documentation', 'examples', or 'ddl'")
        except Exception as e:
            error_msg = f"Error in add_manual_context: {str(e)}"
            print(error_msg)
            return error_msg

    def load_context_from_file(self, file_path, context_type):
        """
        Load context from a file and add it to Vanna AI
        
        Args:
            file_path: Path to the file containing context
            context_type: Type of context ('documentation', 'examples', or 'ddl')
        
        Returns:
            Result message from training
        """
        try:
            # Check if the file path is absolute or relative
            if not os.path.isabs(file_path):
                # Try different base directories
                possible_paths = [
                    file_path,  # Original path (relative to current directory)
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path),  # Relative to script location
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), "contexts", file_path)  # In contexts subdirectory
                ]
                
                file_found = False
                for path in possible_paths:
                    if os.path.exists(path):
                        file_path = path
                        file_found = True
                        print(f"Found context file at: {file_path}")
                        break
                        
                if not file_found:
                    return f"Error: Could not find file at any of these locations: {', '.join(possible_paths)}"
                    
            print(f"Loading context from file: {file_path} of type: {context_type}")
            
            with open(file_path, 'r') as file:
                content = file.read()
                
            return self.add_manual_context(context_type, content)
        except Exception as e:
            error_msg = f"Error loading context from {file_path}: {str(e)}"
            print(error_msg)
            return error_msg

    def setup_complete_context(self, bigquery_dataset_id=None, 
                            documentation_path=None, 
                            examples_path=None, 
                            ddl_path=None):
        """
        Set up complete context by combining schema extraction with manual context
        
        Args:
            bigquery_dataset_id: Optional BigQuery dataset ID to extract schema
            documentation_path: Optional path to documentation file
            examples_path: Optional path to examples JSON file
            ddl_path: Optional path to custom DDL file
        
        Returns:
            Dictionary with results of each context addition
        """
        results = {}
        
        # Step 1: Extract schema from BigQuery if provided
        if bigquery_dataset_id:
            try:
                schema_result = self.connect_to_bigquery_schema(bigquery_dataset_id)
                results["schema"] = schema_result
            except Exception as e:
                results["schema"] = f"Error extracting schema: {str(e)}"
        
        # Step 2: Add documentation if provided
        if documentation_path:
            try:
                print(f"Setting up documentation context from: {documentation_path}")
                doc_result = self.load_context_from_file(documentation_path, 'documentation')
                results["documentation"] = doc_result
            except Exception as e:
                error_msg = f"Error adding documentation: {str(e)}"
                print(error_msg)
                results["documentation"] = error_msg
        
        # Step 3: Add examples if provided
        if examples_path:
            try:
                print(f"Setting up examples context from: {examples_path}")
                examples_result = self.load_context_from_file(examples_path, 'examples')
                results["examples"] = examples_result
            except Exception as e:
                error_msg = f"Error adding examples: {str(e)}"
                print(error_msg)
                results["examples"] = error_msg
        
        # Step 4: Add custom DDL if provided
        if ddl_path:
            try:
                print(f"Setting up DDL context from: {ddl_path}")
                ddl_result = self.load_context_from_file(ddl_path, 'ddl')
                results["ddl"] = ddl_result
            except Exception as e:
                error_msg = f"Error adding DDL: {str(e)}"
                print(error_msg)
                results["ddl"] = error_msg
        
        return results 

    def store_query_pair(self, question: str, sql: str, execution_time: float, 
                        was_successful: bool, result_preview: Optional[str] = None):
        """
        Store a question-SQL pair in MongoDB with vector embedding
        
        Args:
            question: The natural language question
            sql: The generated SQL query
            execution_time: Time taken to execute the query (in seconds)
            was_successful: Whether the query executed successfully
            result_preview: Optional preview of the results
        """
        # Generate embedding for the question
        embedding = self.model.encode(question).tolist()
        
        # Create document for MongoDB
        document = {
            "question": question,
            "sql": sql,
            "embedding": embedding,
            "execution_time": execution_time,
            "was_successful": was_successful,
            "timestamp": datetime.now()
        }
        
        if result_preview:
            document["result_preview"] = result_preview
            
        # Generate a unique ID using question
        id = hashlib.md5(question.encode()).hexdigest()
        document["_id"] = id
        
        # Upsert to collection (update if exists, insert if not)
        self.collection.replace_one({"_id": id}, document, upsert=True)
        
    def find_similar_queries(self, question: str, top_k: int = 3) -> List[Dict]:
        """
        Find similar queries to the input question based on vector similarity
        
        Args:
            question: The natural language question
            top_k: Number of similar queries to return
        
        Returns:
            List of similar query pairs with their metadata
        """
        # Generate embedding for the question
        embedding = self.model.encode(question).tolist()
        
        try:
            # First try vector search if available (MongoDB Atlas)
            similar_queries = self._vector_search(embedding, top_k)
            if similar_queries:
                return similar_queries
        except Exception as e:
            print(f"Vector search error: {e}")
            
        # Fall back to text search if vector search fails or returns no results
        return self._text_search(question, top_k)
    
    def _vector_search(self, embedding: List[float], top_k: int) -> List[Dict]:
        """Perform vector similarity search using MongoDB Atlas Vector Search"""
        try:
            # Use MongoDB's $vectorSearch operator (Atlas only)
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index",
                        "queryVector": embedding,
                        "numCandidates": top_k * 10,  # Search through more candidates for better results
                        "limit": top_k,
                        "path": "embedding"
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "question": 1,
                        "sql": 1,
                        "was_successful": 1,
                        "execution_time": 1,
                        "score": {"$meta": "vectorSearchScore"}
                    }
                }
            ]
            
            results = list(self.collection.aggregate(pipeline))
            return results
        except Exception as e:
            # If Atlas vector search is not available, return empty list
            print(f"Vector search not available: {e}")
            return []
    
    def _text_search(self, question: str, top_k: int) -> List[Dict]:
        """Fall back to simple text search using MongoDB text index"""
        # Extract keywords from question
        keywords = [word for word in question.lower().split() if len(word) > 3]
        
        # Find documents matching any of these keywords
        results = list(self.collection.find(
            {"question": {"$regex": "|".join(keywords), "$options": "i"}},
            {"_id": 0, "question": 1, "sql": 1, "was_successful": 1, "execution_time": 1}
        ).limit(top_k))
        
        return results
    
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
            # Add examples to improve generation , allow_llm_to_see_data=True
            sql = self.vn.generate_sql(question=question, examples=example_pairs, allow_llm_to_see_data=True)
        else:
            # Generate without examples
            sql = self.vn.generate_sql(question=question, allow_llm_to_see_data=True)
        
        # Add this before returning TEMPORARY FOR DEBUGGING
        if "membership_groceries_userprofile" in sql:
            sql = sql.replace("membership_groceries_userprofile", "sqlAgentTestv1.groceries")
            
        return sql, similar_queries
    
    def execute_query(self, sql: str) -> Tuple[bigquery.table.RowIterator, float]:
        """
        Execute a SQL query on BigQuery and measure execution time
        
        Args:
            sql: SQL query to execute
        
        Returns:
            Query results and execution time
        """
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
        Get history of stored queries from MongoDB
        
        Args:
            limit: Maximum number of queries to return
        
        Returns:
            List of query pairs with metadata
        """
        # Get most recent queries
        history = list(self.collection.find(
            {}, 
            {
                "_id": 0, 
                "question": 1, 
                "sql": 1, 
                "was_successful": 1, 
                "execution_time": 1, 
                "timestamp": 1
            }
        ).sort("timestamp", -1).limit(limit))
        
        # Convert MongoDB datetime to string for JSON serialization
        for entry in history:
            if "timestamp" in entry:
                entry["timestamp"] = entry["timestamp"].isoformat()
                
        return history
    
    def _is_datetime(self, series):
        """Helper method to check if a series can be converted to datetime"""
        try:
            # Try to parse with a more explicit format parameter
            pd.to_datetime(series, errors='coerce', infer_datetime_format=True)
            return True
        except:
            return False

    def _generate_insights_with_gemini(self, data, analysis_results, sql_query=None, documentation=None):
        """
        Use Google's Gemini AI model to generate insights from the data analysis results,
        incorporating SQL query context and dataset documentation when available
        
        Args:
            data: Either a pandas DataFrame or a list of dictionaries (the original data)
            analysis_results: The statistical analysis results dictionary
            sql_query: Optional; The SQL query that generated the data
            documentation: Optional; Documentation about the dataset schema/structure
                
        Returns:
            Dictionary with AI-generated insights
        """
        print("Starting Gemini insights generation")
        try:
            # Load environment variables and configure Gemini API
            try:
                load_dotenv()
                gemini_api_key = os.getenv("GEMINI_API_KEY")
                if not gemini_api_key:
                    print("ERROR: GEMINI_API_KEY not found in environment variables")
                    return {"error": "GEMINI_API_KEY not found in environment variables"}
                
                print(f"Using Gemini API key: {gemini_api_key[:4]}...{gemini_api_key[-4:]}")
                genai.configure(api_key=gemini_api_key)
                print("Gemini API configured successfully")
            except Exception as e:
                print(f"Detailed error configuring Gemini API: {repr(e)}")
                return {"error": f"Could not configure Gemini API: {str(e)}"}
            
            # Convert data and analysis to string formats for Gemini
            try:
                # Safely convert data to string representation
                if isinstance(data, pd.DataFrame):
                    try:
                        # Limit to 10 rows and handle potential display issues
                        data_sample = data.head(10).to_string(index=False)
                    except Exception as e:
                        print(f"Error converting DataFrame to string: {e}")
                        # Fallback to simple column names if conversion fails
                        data_sample = f"DataFrame with columns: {', '.join(data.columns.tolist())}"
                else:
                    try:
                        # Limit to 10 items and handle potential serialization issues
                        safe_data = []
                        for item in data[:10]:
                            try:
                                # Create a sanitized copy with string-safe values
                                safe_item = {}
                                for key, value in item.items():
                                    try:
                                        # Attempt to convert each value to a string-safe representation
                                        if pd.isna(value):
                                            safe_item[key] = "NULL"
                                        elif isinstance(value, (int, float, str, bool, type(None))):
                                            safe_item[key] = value
                                        else:
                                            safe_item[key] = str(value)
                                    except:
                                        safe_item[key] = "CONVERSION_ERROR"
                                safe_data.append(safe_item)
                            except:
                                # Skip items that can't be processed
                                pass
                        data_sample = json.dumps(safe_data, indent=2)
                    except Exception as e:
                        print(f"Error converting list data to string: {e}")
                        data_sample = "Data could not be converted to string format"
                
                # Safely convert analysis results to string
                try:
                    # Create a sanitized copy of analysis_results
                    safe_analysis = {}
                    # Add only simple key values that are likely to serialize well
                    safe_keys = ["row_count", "column_count", "insights"]
                    for key in safe_keys:
                        if key in analysis_results:
                            safe_analysis[key] = analysis_results[key]
                    
                    # Add simplified column info
                    if "columns" in analysis_results:
                        safe_analysis["columns"] = {}
                        for col, col_data in analysis_results["columns"].items():
                            safe_col_data = {
                                "type": col_data.get("type", "unknown")
                            }
                            # Add basic stats based on column type
                            if col_data.get("type") == "numeric":
                                for stat in ["min", "max", "mean", "median"]:
                                    if stat in col_data:
                                        safe_col_data[stat] = col_data[stat]
                            elif col_data.get("type") == "categorical":
                                safe_col_data["unique_count"] = col_data.get("unique_count", 0)
                            elif col_data.get("type") == "datetime":
                                if "min_date" in col_data:
                                    safe_col_data["min_date"] = col_data["min_date"]
                                if "max_date" in col_data:
                                    safe_col_data["max_date"] = col_data["max_date"]
                            
                            safe_analysis["columns"][col] = safe_col_data
                    
                    analysis_json = json.dumps(safe_analysis, indent=2)
                    print(f"Analysis data prepared successfully, size: {len(analysis_json)}")
                except Exception as e:
                    print(f"Error converting analysis results to JSON: {e}")
                    analysis_json = json.dumps({"error": "Could not convert analysis to JSON"})
                
                # Create a prompt for Gemini that integrates all available information
                prompt_parts = [
                    "I have a dataset with the following sample data:\n\n",
                    f"{data_sample}\n\n",
                    "I've performed statistical analysis on this data and here are the results:\n\n",
                    f"{analysis_json}\n\n",
                ]
                
                # Add SQL query context if available
                if sql_query:
                    prompt_parts.extend([
                        "This data was generated using the following SQL query:\n\n",
                        f"```sql\n{sql_query}\n```\n\n",
                        "This query context should help you understand what the user was looking for in the data.\n\n"
                    ])
                
                # Add dataset documentation if available
                if documentation:
                    prompt_parts.extend([
                        "Here is documentation about the dataset schema and business context:\n\n",
                        f"{documentation}\n\n",
                        "Use this documentation to provide insights based on the business meaning of the data.\n\n"
                    ])
                
                # Add the request for analysis
                prompt_parts.extend([
                    "Based on all this information, please provide:\n",
                    "1. A concise executive summary of the dataset (2-3 sentences)\n",
                    "2. 3-5 key insights or patterns observed in the data\n",
                    "3. Recommended next steps for further analysis or actions\n",
                    "4. Any potential issues or limitations with the data\n",
                    
                    "Format your response as a JSON with the following structure:\n",
                    "{\n",
                    '    "executive_summary": "...",\n',
                    '    "key_insights": ["insight 1", "insight 2", ...],\n',
                    '    "recommended_steps": ["step 1", "step 2", ...],\n',
                    '    "data_limitations": ["limitation 1", "limitation 2", ...]\n',
                    "}\n\n",
                    
                    "Ensure that your insights are specific to this dataset and based on the statistical analysis provided."
                ])
                
                prompt = "".join(prompt_parts)
                print(f"Prompt created successfully, length: {len(prompt)}")
                
                # Generate content with Gemini
                try:
                    # Try with gemini-1.0-pro first as it's more likely to be available
                    print("Attempting to use gemini-1.0-pro model")
                    safety_settings = [
                        {
                            "category": "HARM_CATEGORY_HARASSMENT",
                            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                        },
                        {
                            "category": "HARM_CATEGORY_HATE_SPEECH",
                            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                        },
                        {
                            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                        },
                        {
                            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                        }
                    ]
                    
                    generation_config = {
                        "temperature": 0.4,
                        "top_p": 0.95,
                        "top_k": 40,
                        "max_output_tokens": 2048,
                    }
                    
                    # First try with gemini-1.0-pro (more widely available)
                    try:
                        model = genai.GenerativeModel(
                            model_name='gemini-1.0-pro',
                            safety_settings=safety_settings,
                            generation_config=generation_config
                        )
                        
                        print("Calling Gemini API with gemini-1.0-pro model")
                        response = model.generate_content(prompt)
                        print("Gemini API call successful with gemini-1.0-pro")
                    except Exception as e:
                        print(f"Error with gemini-1.0-pro, attempting fallback: {e}")
                        # Fallback to other models if first one fails
                        try:
                            model = genai.GenerativeModel(
                                model_name='gemini-2.0-flash',
                                safety_settings=safety_settings,
                                generation_config=generation_config
                            )
                            
                            print("Calling Gemini API with gemini-2.0-flash model")
                            response = model.generate_content(prompt)
                            print("Gemini API call successful with gemini-2.0-flash")
                        except Exception as e2:
                            print(f"Error with gemini-2.0-flash too, using final fallback: {e2}")
                            # Final fallback
                            model = genai.GenerativeModel(
                                model_name='gemini-pro',  # Even more basic fallback
                                safety_settings=safety_settings,
                                generation_config=generation_config
                            )
                            
                            print("Calling Gemini API with gemini-pro model")
                            response = model.generate_content(prompt)
                            print("Gemini API call successful with gemini-pro")
                except Exception as e:
                    print(f"All Gemini model attempts failed: {repr(e)}")
                    # Generate a basic fallback response
                    return self._generate_basic_insights(data, analysis_results)
                
                # Extract and parse JSON response
                try:
                    # Get the response text
                    content_text = response.text
                    print(f"Received response from Gemini, length: {len(content_text)}")
                    
                    # Sometimes the response might contain markdown code blocks
                    if "```json" in content_text:
                        content_text = content_text.split("```json")[1].split("```")[0].strip()
                        print("Extracted JSON from markdown code block")
                    elif "```" in content_text:
                        content_text = content_text.split("```")[1].split("```")[0].strip()
                        print("Extracted content from markdown code block")
                    
                    # Parse the JSON response
                    try:
                        gemini_insights = json.loads(content_text)
                        print("Successfully parsed JSON response")
                        
                        # Verify the expected structure is present
                        if not isinstance(gemini_insights, dict):
                            print("Response is not a dictionary, converting")
                            gemini_insights = {"gemini_analysis": str(gemini_insights)}
                        
                        # Ensure we have all expected keys with proper types
                        if "executive_summary" not in gemini_insights or not isinstance(gemini_insights["executive_summary"], str):
                            print("Adding missing executive_summary")
                            gemini_insights["executive_summary"] = "Summary not available"
                        
                        if "key_insights" not in gemini_insights or not isinstance(gemini_insights["key_insights"], list):
                            print("Adding missing key_insights")
                            gemini_insights["key_insights"] = ["No specific insights available"]
                        
                        if "recommended_steps" not in gemini_insights or not isinstance(gemini_insights["recommended_steps"], list):
                            print("Adding missing recommended_steps")
                            gemini_insights["recommended_steps"] = ["No specific recommendations available"]
                        
                        if "data_limitations" not in gemini_insights or not isinstance(gemini_insights["data_limitations"], list):
                            print("Adding missing data_limitations")
                            gemini_insights["data_limitations"] = ["No specific limitations identified"]
                        
                        return gemini_insights
                    except json.JSONDecodeError as parse_error:
                        print(f"Error parsing Gemini response as JSON: {parse_error}")
                        print(f"Raw response content: {content_text[:200]}...")
                        # Return the raw text if JSON parsing fails
                        return {
                            "executive_summary": "Analysis generated but not in proper format",
                            "key_insights": ["The AI generated a response but it wasn't in the expected JSON format"],
                            "recommended_steps": ["Review the raw analysis text below"],
                            "data_limitations": ["Analysis format issue detected"],
                            "raw_text": content_text
                        }
                except Exception as e:
                    print(f"Error processing Gemini response: {repr(e)}")
                    return self._generate_basic_insights(data, analysis_results)
                    
            except Exception as e:
                print(f"Error preparing data for Gemini: {repr(e)}")
                return self._generate_basic_insights(data, analysis_results)
        except Exception as e:
            print(f"Unhandled error in _generate_insights_with_gemini: {repr(e)}")
            return self._generate_basic_insights(data, analysis_results)
            
    def _generate_basic_insights(self, data, analysis_results):
        """Generate basic insights without using Gemini API"""
        print("Generating basic fallback insights")
        
        # Extract basic statistics from analysis_results
        row_count = analysis_results.get("row_count", 0)
        column_count = analysis_results.get("column_count", 0)
        
        # Get column types if available
        column_types = {}
        if "column_types" in analysis_results:
            column_types = analysis_results["column_types"]
        
        # Count of column by type
        numeric_count = sum(1 for col_type in column_types.values() if col_type == "numeric")
        categorical_count = sum(1 for col_type in column_types.values() if col_type == "categorical")
        datetime_count = sum(1 for col_type in column_types.values() if col_type == "datetime")
        
        return {
            "executive_summary": f"This dataset contains {row_count} rows and {column_count} columns including {numeric_count} numeric, {categorical_count} categorical, and {datetime_count} datetime fields.",
            "key_insights": [
                f"Dataset contains {row_count} rows and {column_count} columns.",
                "Statistical analysis has been performed on all columns.",
                "AI-powered deep analysis unavailable - using basic analysis only."
            ],
            "recommended_steps": [
                "Review the statistical metrics provided for each column.",
                "Consider exploring correlations between numeric columns.",
                "Verify data quality and completeness based on null percentages."
            ],
            "data_limitations": [
                "AI-powered analysis unavailable - using basic fallback.",
                "Limited analysis without natural language insights.",
                "Consider setting up Gemini API for enhanced analytics."
            ]
        }
    
    def test_gemini_connection(self):
        """Test connection to Gemini API"""
        try:
            load_dotenv()
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            if not gemini_api_key:
                return "ERROR: GEMINI_API_KEY not found in environment variables"
            
            print(f"Testing Gemini connection with API key: {gemini_api_key[:4]}...{gemini_api_key[-4:]}")
            
            genai.configure(api_key=gemini_api_key)
            
            # Try different models in order of likelihood of being available
            models_to_try = ['gemini-1.0-pro', 'gemini-pro', 'gemini-2.0-flash']
            
            for model_name in models_to_try:
                try:
                    print(f"Testing with model: {model_name}")
                    model = genai.GenerativeModel(model_name)
                    prompt = "Respond with a single word: Hello"
                    
                    response = model.generate_content(prompt)
                    
                    return f"Gemini API working with model {model_name}: {response.text[:30]}..."
                except Exception as model_error:
                    print(f"Model {model_name} failed: {str(model_error)}")
                    continue
            
            return "ERROR: All Gemini models failed, check API key permissions"
        except Exception as e:
            return f"ERROR: Gemini API test failed: {str(e)}"
    
    def analyze_data(self, data, sql_query=None, documentation=None):
        """
        Perform statistical analysis on the query results data and generate insights using Gemini
        
        Args:
            data: Either a pandas DataFrame or a list of dictionaries
            sql_query: Optional; The SQL query that generated the data
            documentation: Optional; Documentation about the dataset schema/structure
                
        Returns:
            Dictionary with statistical analysis and AI-generated insights
        """
        try:
            import pandas as pd
            import numpy as np
            
            # Convert to DataFrame if not already
            try:
                if not isinstance(data, pd.DataFrame):
                    df = pd.DataFrame(data)
                else:
                    df = data.copy()  # Make a copy to avoid modifying the original
            except Exception as e:
                print(f"Error converting data to DataFrame: {e}")
                return {"error": f"Could not convert data to DataFrame: {str(e)}"}
            
            if df.empty:
                return {"error": "No data to analyze"}
            
            analysis = {}
            
            try:
                # Basic dataset info - always include these
                analysis["row_count"] = int(len(df))
                analysis["column_count"] = int(len(df.columns))
                
                # Get column types
                column_types = {}
                numeric_columns = []
                categorical_columns = []
                datetime_columns = []
                
                for col in df.columns:
                    try:
                        if pd.api.types.is_numeric_dtype(df[col]):
                            column_types[col] = "numeric"
                            numeric_columns.append(col)
                        elif pd.api.types.is_datetime64_dtype(df[col]) or self._is_datetime(df[col]):
                            column_types[col] = "datetime"
                            datetime_columns.append(col)
                        else:
                            column_types[col] = "categorical"
                            categorical_columns.append(col)
                    except Exception as e:
                        print(f"Error determining type for column {col}: {e}")
                        column_types[col] = "unknown"
                
                analysis["column_types"] = column_types
                analysis["columns"] = {}
                
                # Analyze each column
                for col in df.columns:
                    try:
                        col_analysis = {
                            "type": column_types.get(col, "unknown")
                        }
                        
                        # Safe null count calculation
                        try:
                            null_count = int(df[col].isna().sum())
                            null_percentage = float(round(null_count / max(len(df), 1) * 100, 2))
                            col_analysis["null_count"] = null_count
                            col_analysis["null_percentage"] = null_percentage
                        except Exception as e:
                            print(f"Error calculating null values for {col}: {e}")
                            col_analysis["null_count"] = 0
                            col_analysis["null_percentage"] = 0.0
                        
                        # For numeric columns, add statistical measures
                        if column_types.get(col) == "numeric":
                            try:
                                # Handle each statistic separately to avoid one error breaking all
                                try:
                                    min_val = df[col].min()
                                    col_analysis["min"] = float(min_val) if not pd.isna(min_val) else None
                                except Exception as e:
                                    print(f"Error calculating min for {col}: {e}")
                                    col_analysis["min"] = None
                                    
                                try:
                                    max_val = df[col].max()
                                    col_analysis["max"] = float(max_val) if not pd.isna(max_val) else None
                                except Exception as e:
                                    print(f"Error calculating max for {col}: {e}")
                                    col_analysis["max"] = None
                                    
                                try:
                                    mean_val = df[col].mean()
                                    col_analysis["mean"] = float(mean_val) if not pd.isna(mean_val) else None
                                except Exception as e:
                                    print(f"Error calculating mean for {col}: {e}")
                                    col_analysis["mean"] = None
                                    
                                try:
                                    median_val = df[col].median()
                                    col_analysis["median"] = float(median_val) if not pd.isna(median_val) else None
                                except Exception as e:
                                    print(f"Error calculating median for {col}: {e}")
                                    col_analysis["median"] = None
                                    
                                try:
                                    std_val = df[col].std()
                                    col_analysis["std_dev"] = float(std_val) if not pd.isna(std_val) else None
                                except Exception as e:
                                    print(f"Error calculating std_dev for {col}: {e}")
                                    col_analysis["std_dev"] = None
                                
                                # Outlier detection - very safely
                                try:
                                    if not df[col].isna().all() and len(df[col].dropna()) > 2:
                                        mean_val = df[col].mean()
                                        std_val = df[col].std()
                                        
                                        # Only proceed if std_dev is not zero to avoid division by zero
                                        if std_val > 0:
                                            z_scores = np.abs((df[col] - mean_val) / std_val)
                                            outlier_mask = z_scores > 3
                                            
                                            if outlier_mask.any():
                                                # Convert to list safely
                                                try:
                                                    outliers = df.loc[outlier_mask, col].tolist()
                                                    safe_outliers = []
                                                    
                                                    # Convert each outlier safely
                                                    for x in outliers[:5]:  # Limit to 5 examples
                                                        try:
                                                            safe_outliers.append(float(x))
                                                        except:
                                                            # If conversion fails, skip this outlier
                                                            pass
                                                    
                                                    if safe_outliers:
                                                        col_analysis["potential_outliers"] = safe_outliers
                                                        col_analysis["outlier_count"] = int(outlier_mask.sum())
                                                except Exception as e:
                                                    print(f"Error processing outliers for {col}: {e}")
                                except Exception as e:
                                    print(f"Error in outlier detection for {col}: {e}")
                            except Exception as e:
                                print(f"Error analyzing numeric column {col}: {e}")
                        
                        # For categorical columns, add frequency analysis
                        elif column_types.get(col) == "categorical":
                            try:
                                # Safely get unique count
                                try:
                                    col_analysis["unique_count"] = int(df[col].nunique())
                                except Exception as e:
                                    print(f"Error calculating unique count for {col}: {e}")
                                    col_analysis["unique_count"] = 0
                                
                                # Safely get value counts
                                try:
                                    value_counts = df[col].value_counts().head(5).to_dict()
                                    # Convert keys and values to ensure they're JSON serializable
                                    safe_value_counts = {}
                                    for k, v in value_counts.items():
                                        try:
                                            safe_value_counts[str(k)] = int(v)
                                        except:
                                            # Skip this key-value pair if conversion fails
                                            pass
                                    
                                    if safe_value_counts:
                                        col_analysis["top_values"] = safe_value_counts
                                except Exception as e:
                                    print(f"Error calculating value counts for {col}: {e}")
                            except Exception as e:
                                print(f"Error analyzing categorical column {col}: {e}")
                        
                        # For datetime columns, add time-related analysis
                        elif column_types.get(col) == "datetime":
                            try:
                                datetime_series = pd.to_datetime(df[col], errors='coerce')
                                
                                # Safely get min date
                                try:
                                    min_date = datetime_series.min()
                                    col_analysis["min_date"] = min_date.isoformat() if not pd.isna(min_date) else None
                                except Exception as e:
                                    print(f"Error getting min date for {col}: {e}")
                                    col_analysis["min_date"] = None
                                
                                # Safely get max date
                                try:
                                    max_date = datetime_series.max()
                                    col_analysis["max_date"] = max_date.isoformat() if not pd.isna(max_date) else None
                                except Exception as e:
                                    print(f"Error getting max date for {col}: {e}")
                                    col_analysis["max_date"] = None
                                
                                # Safely calculate date range
                                try:
                                    min_date = datetime_series.min()
                                    max_date = datetime_series.max()
                                    if not pd.isna(min_date) and not pd.isna(max_date):
                                        col_analysis["date_range_days"] = int((max_date - min_date).days)
                                except Exception as e:
                                    print(f"Error calculating date range for {col}: {e}")
                            except Exception as e:
                                print(f"Error analyzing datetime column {col}: {e}")
                                # If conversion fails, treat as categorical
                                col_analysis["type"] = "categorical"
                                try:
                                    col_analysis["unique_count"] = int(df[col].nunique())
                                    
                                    try:
                                        value_counts = df[col].value_counts().head(5).to_dict()
                                        # Convert keys and values to ensure they're JSON serializable
                                        safe_value_counts = {}
                                        for k, v in value_counts.items():
                                            try:
                                                safe_value_counts[str(k)] = int(v)
                                            except:
                                                # Skip this key-value pair if conversion fails
                                                pass
                                        
                                        if safe_value_counts:
                                            col_analysis["top_values"] = safe_value_counts
                                    except Exception as sub_e:
                                        print(f"Error calculating value counts for {col}: {sub_e}")
                                except Exception as sub_e:
                                    print(f"Error getting fallback categorical stats for {col}: {sub_e}")
                        
                        analysis["columns"][col] = col_analysis
                    except Exception as e:
                        print(f"Skipping analysis for column {col} due to error: {e}")
                        # Add minimal info for this column to avoid missing keys
                        analysis["columns"][col] = {"type": "unknown", "error": str(e)}
                
                # Basic overall dataset insights
                insights = []
                
                # Row count insight
                try:
                    if len(df) > 1000:
                        insights.append(f"Large dataset with {len(df)} rows.")
                    elif len(df) < 5:
                        insights.append(f"Very small dataset with only {len(df)} rows.")
                except Exception as e:
                    print(f"Error generating row count insight: {e}")
                
                # Missing values insight
                try:
                    missing_cols = []
                    for col in df.columns:
                        try:
                            null_percentage = analysis["columns"][col].get("null_percentage", 0)
                            if null_percentage > 0:
                                missing_cols.append((col, null_percentage))
                        except Exception as e:
                            print(f"Error checking missing values for {col}: {e}")
                    
                    if missing_cols:
                        top_missing = sorted(missing_cols, key=lambda x: x[1], reverse=True)[:3]
                        insights.append(f"Missing values detected in {len(missing_cols)} columns. " +
                                    f"Most affected: {', '.join([f'{col} ({pct}%)' for col, pct in top_missing])}")
                except Exception as e:
                    print(f"Error generating missing values insight: {e}")
                
                # Add column-specific insights
                try:
                    for col in numeric_columns:
                        try:
                            col_data = analysis["columns"][col]
                            if "outlier_count" in col_data and col_data["outlier_count"] > 0:
                                outlier_pct = round(col_data["outlier_count"] / len(df) * 100, 1)
                                insights.append(f"Potential outliers detected in '{col}' ({outlier_pct}% of values).")
                        except Exception as e:
                            print(f"Error generating outlier insight for {col}: {e}")
                except Exception as e:
                    print(f"Error generating column-specific insights: {e}")
                
                analysis["insights"] = insights
            except Exception as e:
                print(f"Error in main analysis: {e}")
                # Ensure we have at least some basic structure
                analysis.setdefault("row_count", 0)
                analysis.setdefault("column_count", 0)
                analysis.setdefault("column_types", {})
                analysis.setdefault("columns", {})
                analysis.setdefault("insights", [f"Analysis error: {str(e)}"])
            
            # Generate AI insights with Gemini, passing SQL query and documentation
            try:
                gemini_insights = self._generate_insights_with_gemini(data, analysis, sql_query, documentation)
                analysis["ai_analysis"] = gemini_insights
            except Exception as e:
                print(f"Error generating Gemini insights: {e}")
                analysis["ai_analysis"] = {"error": f"Could not generate AI insights: {str(e)}"}
            
            return analysis
        except Exception as e:
            print(f"Critical error in analyze_data: {e}")
            # Return minimal valid response
            return {
                "error": f"Analysis failed: {str(e)}",
                "row_count": 0,
                "column_count": 0,
                "columns": {},
                "insights": [f"Analysis error: {str(e)}"],
                "ai_analysis": {"error": "Analysis failed"}
            }

    def suggest_visualizations(self, data):
        """
        Suggest appropriate visualization types for the data
        
        Args:
            data: Either a pandas DataFrame or a list of dictionaries
            
        Returns:
            Dictionary with visualization suggestions
        """
        import pandas as pd
        
        # Convert to DataFrame if not already
        if not isinstance(data, pd.DataFrame):
            df = pd.DataFrame(data)
        else:
            df = data
        
        if df.empty:
            return {"error": "No data to visualize"}
        
        # Identify column types
        numeric_columns = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
        categorical_columns = []
        datetime_columns = []
        
        for col in df.columns:
            if col in numeric_columns:
                continue
            elif pd.api.types.is_datetime64_dtype(df[col]) or self._is_datetime(df[col]):
                datetime_columns.append(col)
            else:
                categorical_columns.append(col)
        
        suggestions = {
            "recommended_chart": None,
            "possible_charts": [],
            "column_roles": {
                "metrics": numeric_columns,
                "dimensions": categorical_columns + datetime_columns
            }
        }
        
        # Determine possible chart types based on data structure
        
        # Line chart suggestion
        if datetime_columns and numeric_columns:
            suggestions["possible_charts"].append({
                "type": "line",
                "suitability": "high",
                "reason": "Time series data detected",
                "suggested_config": {
                    "x_axis": datetime_columns[0],
                    "y_axis": numeric_columns[0],
                    "series": categorical_columns[0] if categorical_columns else None
                }
            })
            # Set as recommended if we have time and numeric data
            if not suggestions["recommended_chart"]:
                suggestions["recommended_chart"] = "line"
        
        # Bar chart suggestion
        if categorical_columns and numeric_columns:
            category_count = df[categorical_columns[0]].nunique() if categorical_columns else 0
            
            if 1 <= category_count <= 20:  # Reasonable number of categories for a bar chart
                suggestions["possible_charts"].append({
                    "type": "bar",
                    "suitability": "high" if category_count <= 10 else "medium",
                    "reason": f"Categorical data with {category_count} categories",
                    "suggested_config": {
                        "x_axis": categorical_columns[0],
                        "y_axis": numeric_columns[0],
                        "group_by": categorical_columns[1] if len(categorical_columns) > 1 else None
                    }
                })
                # Set as recommended if we have categorical data and not already recommended line chart
                if not suggestions["recommended_chart"]:
                    suggestions["recommended_chart"] = "bar"
        
        # Pie chart suggestion
        if categorical_columns and numeric_columns:
            category_count = df[categorical_columns[0]].nunique() if categorical_columns else 0
            
            if 2 <= category_count <= 6:  # Good number of categories for a pie chart
                suggestions["possible_charts"].append({
                    "type": "pie",
                    "suitability": "high",
                    "reason": f"Small number of categories ({category_count})",
                    "suggested_config": {
                        "name": categorical_columns[0],
                        "value": numeric_columns[0]
                    }
                })
                # Set as recommended if optimal for pie chart
                if category_count <= 5 and not suggestions["recommended_chart"]:
                    suggestions["recommended_chart"] = "pie"
        
        # Scatter plot suggestion
        if len(numeric_columns) >= 2:
            suggestions["possible_charts"].append({
                "type": "scatter",
                "suitability": "medium",
                "reason": "Multiple numeric columns available",
                "suggested_config": {
                    "x_axis": numeric_columns[0],
                    "y_axis": numeric_columns[1],
                    "size": numeric_columns[2] if len(numeric_columns) > 2 else None,
                    "color": categorical_columns[0] if categorical_columns else None
                }
            })
        
        # If no chart type is recommended yet, default to table
        if not suggestions["recommended_chart"] and len(df.columns) > 0:
            suggestions["recommended_chart"] = "table"
            suggestions["possible_charts"].append({
                "type": "table",
                "suitability": "high",
                "reason": "Data structure best represented as a table"
            })
        
        return suggestions
    
    def reset_vanna_memory(self):
        """
        Reset the Vanna AI instance by recreating it with the same configuration
        but without any previous training data or context.
        
        Returns:
            str: Status message
        """
        try:
            # Save the current API key and other settings
            api_key = self.vn.api_key if hasattr(self.vn, 'api_key') else None
            model_name = self.vn.model if hasattr(self.vn, 'model') else 'data-analyst-agent-2'
            
            # Create a fresh instance with the same configuration
            self.vn = VannaDefault(model=model_name, api_key=api_key)
            
            # Re-setup the run_sql function
            self._setup_vanna_run_sql()
            
            return "Vanna AI memory has been reset successfully"
        except Exception as e:
            error_msg = f"Error resetting Vanna AI memory: {str(e)}"
            print(error_msg)
            return error_msg

    def clear_query_history(self):
        """
        Clear all stored query history from MongoDB collection
        
        Returns:
            str: Status message
        """
        try:
            result = self.collection.delete_many({})
            deleted_count = result.deleted_count
            return f"Successfully cleared {deleted_count} query history records"
        except Exception as e:
            error_msg = f"Error clearing query history: {str(e)}"
            print(error_msg)
            return error_msg