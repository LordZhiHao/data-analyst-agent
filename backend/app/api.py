"""
FastAPI REST API for the Vanna SQL Agent.
Provides endpoints for querying, schema connection, history, and more.
"""

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any

# from .agent import SQLAgent
from .mongodbAgent import MongoDBSQLAgent
from .config import settings
import db_dtypes

app = FastAPI(
    title="Vanna AI SQL Agent API",
    description="Natural language to SQL conversion with approval workflow",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize SQLAgent with MongoDB
agent = MongoDBSQLAgent(
    vanna_api_key=settings.VANNA_API_KEY,
    bigquery_credentials_path=settings.BIGQUERY_CREDENTIALS_PATH,
    mongo_uri=settings.MONGO_URI,
    db_name=settings.MONGO_DB_NAME,
    collection_name=settings.MONGO_COLLECTION_NAME
)

# Input models
class QuestionRequest(BaseModel):
    question: str
    store_results: bool = True
    require_approval: bool = True
    approved: bool = False

class SchemaRequest(BaseModel):
    dataset_id: str

class DirectSQLRequest(BaseModel):
    sql: str
    store_results: bool = False

class QuestionSQLPairRequest(BaseModel):
    question: str
    sql: str
    store_results: bool = True

class AnalysisRequest(BaseModel):
    data: List[Dict[str, Any]]

class VisualizationRequest(BaseModel):
    data: List[Dict[str, Any]]

# API endpoints
@app.post("/analyze-data", tags=["analysis"])
async def analyze_data(request: AnalysisRequest):
    """
    Analyze data and provide statistical insights
    """
    try:
        if not request.data:
            return {
                "error": "No data provided",
                "row_count": 0,
                "column_count": 0,
                "columns": {},
                "insights": ["No data to analyze"],
                "ai_analysis": {"error": "No data provided"}
            }
        
        analysis_results = agent.analyze_data(request.data)
        return analysis_results
    except Exception as e:
        error_message = str(e)
        print(f"Error in analyze-data endpoint: {error_message}")
        # Return a structured response even on error
        return {
            "error": f"Analysis failed: {error_message}",
            "row_count": 0,
            "column_count": 0,
            "columns": {},
            "insights": [f"Analysis error: {error_message}"],
            "ai_analysis": {"error": f"Analysis failed: {error_message}"}
        }

@app.post("/suggest-visualizations", tags=["analysis"])
async def suggest_visualizations(request: VisualizationRequest):
    """
    Suggest appropriate visualization types for the data
    """
    try:
        visualization_suggestions = agent.suggest_visualizations(request.data)
        return visualization_suggestions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=Dict[str, Any], tags=["queries"])
async def query(request: QuestionRequest):
    """
    Convert natural language to SQL, execute on BigQuery, and return results.
    If require_approval is True and approved is False, will only return the generated SQL without executing.
    """
    try:
        result = agent.query(
            question=request.question,
            store_results=request.store_results,
            require_approval=request.require_approval,
            approved=request.approved
        )
        
        # Convert DataFrame to dict for JSON serialization if exists
        if "results" in result and result["results"] is not None:
            result["results"] = result["results"].to_dict(orient="records")
            
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/connect-schema", tags=["schema"])
async def connect_schema(request: SchemaRequest):
    """
    Connect to a BigQuery dataset schema to improve SQL generation
    """
    try:
        result = agent.connect_to_bigquery_schema(request.dataset_id)
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/similar-queries/{question}", tags=["queries"])
async def get_similar_queries(question: str, top_k: int = 3):
    """
    Find similar queries to the input question based on semantic similarity
    """
    try:
        similar_queries = agent.find_similar_queries(question, top_k=top_k)
        return {"similar_queries": similar_queries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history", tags=["history"])
async def get_history(limit: int = 10):
    """
    Get history of stored queries from the vector database
    """
    try:
        history = agent.get_query_history(limit=limit)
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-sql", tags=["queries"])
async def generate_sql(request: QuestionRequest):
    """
    Generate SQL from natural language without executing the query
    """
    try:
        sql, similar_queries = agent.generate_sql(request.question)
        return {
            "question": request.question,
            "sql": sql,
            "similar_queries": similar_queries
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/direct-sql", tags=["queries"])
async def direct_sql(request: DirectSQLRequest):
    """
    Execute a SQL query directly without natural language processing
    """
    try:
        # Execute the query directly
        results, execution_time = agent.execute_query(request.sql)
        
        # Convert to DataFrame for easier manipulation
        df = results.to_dataframe()
        
        # Prepare response
        response = {
            "sql": request.sql,
            "was_successful": True,
            "execution_time": execution_time,
            "results": df.to_dict(orient="records")
        }
        
        return response
    
    except Exception as e:
        return {
            "sql": request.sql,
            "was_successful": False,
            "error_message": str(e)
        }

@app.post("/store-question-sql-pair", tags=["queries"])
async def store_question_sql_pair(request: QuestionSQLPairRequest):
    """
    Store a question-SQL pair and execute the SQL query
    """
    try:
        # Execute the query
        results, execution_time = agent.execute_query(request.sql)
        
        # Convert to DataFrame for easier manipulation
        df = results.to_dataframe()
        
        # Get a preview as string
        result_preview = df.head(5).to_string() if not df.empty else "No results"
        
        was_successful = True
        
        # Store the query pair if requested
        if request.store_results:
            agent.store_query_pair(
                question=request.question,
                sql=request.sql,
                execution_time=execution_time,
                was_successful=was_successful,
                result_preview=result_preview
            )
        
        # Prepare response
        response = {
            "question": request.question,
            "sql": request.sql,
            "was_successful": was_successful,
            "execution_time": execution_time,
            "results": df.to_dict(orient="records"),
            "result_preview": result_preview,
            "stored": request.store_results
        }
        
        return response
    
    except Exception as e:
        was_successful = False
        error_message = str(e)
        
        # Still store the unsuccessful query if requested
        if request.store_results:
            try:
                agent.store_query_pair(
                    question=request.question,
                    sql=request.sql,
                    execution_time=0,
                    was_successful=False,
                    result_preview=None
                )
            except Exception as store_error:
                error_message += f" (Additionally, failed to store query: {store_error})"
        
        return {
            "question": request.question,
            "sql": request.sql,
            "was_successful": False,
            "error_message": error_message,
            "stored": request.store_results and "failed to store" not in error_message
        }

# Connect to default schema on startup if configured
@app.on_event("startup")
async def startup_event():
    """Initialize the agent with the default dataset if configured"""
    if settings.DEFAULT_DATASET:
        try:
            result = agent.connect_to_bigquery_schema(settings.DEFAULT_DATASET)
            print(result)
        except Exception as e:
            print(f"Error connecting to default dataset: {e}")
        