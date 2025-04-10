from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import uvicorn
import json
from sql_agent import SQLAgent  # Import the SQLAgent class

app = FastAPI(title="Vanna AI SQL Agent API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize SQLAgent
agent = SQLAgent(
    vanna_api_key="your_vanna_api_key",
    bigquery_credentials_path="path/to/your/bigquery_credentials.json",
    vector_db_path="./vector_db"
)

# Connect to BigQuery schema (you can do this at startup)
@app.on_event("startup")
async def startup_event():
    # This will run when the API starts
    agent.connect_to_bigquery_schema("your_dataset_id")
    print("Connected to BigQuery schema")

# Input models
class QuestionRequest(BaseModel):
    question: str
    store_results: bool = True
    require_approval: bool = True
    approved: bool = False

class SchemaRequest(BaseModel):
    dataset_id: str

# API endpoints
@app.post("/query", response_model=Dict[str, Any])
async def query(request: QuestionRequest):
    """
    Convert natural language to SQL, execute on BigQuery, and return results
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

@app.post("/connect-schema")
async def connect_schema(request: SchemaRequest):
    """
    Connect to a BigQuery dataset schema
    """
    try:
        agent.connect_to_bigquery_schema(request.dataset_id)
        return {"message": f"Successfully connected to schema: {request.dataset_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/similar-queries/{question}")
async def get_similar_queries(question: str, top_k: int = 3):
    """
    Find similar queries to the input question
    """
    try:
        similar_queries = agent.find_similar_queries(question, top_k=top_k)
        return {"similar_queries": similar_queries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
async def get_history(limit: int = 10):
    """
    Get history of stored queries
    """
    try:
        history = agent.get_query_history(limit=limit)
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-sql")
async def generate_sql(request: QuestionRequest):
    """
    Generate SQL from natural language without executing
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

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)