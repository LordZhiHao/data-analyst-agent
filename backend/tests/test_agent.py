"""
Tests for the SQLAgent class.
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
import pandas as pd

from app.agent import SQLAgent

@pytest.fixture
def mock_agent():
    """Create a mock SQLAgent with dependencies mocked"""
    with patch('vanna.remote.VannaDefault') as mock_vanna, \
         patch('google.oauth2.service_account.Credentials') as mock_creds, \
         patch('google.cloud.bigquery.Client') as mock_bq_client, \
         patch('chromadb.PersistentClient') as mock_chroma, \
         patch('sentence_transformers.SentenceTransformer') as mock_transformer:
        
        # Setup mocks
        mock_vanna_instance = mock_vanna.return_value
        mock_vanna_instance.generate_sql.return_value = "SELECT * FROM test_table LIMIT 10"
        mock_vanna_instance.train.return_value = None
        
        mock_creds.from_service_account_file.return_value = MagicMock()
        mock_creds.from_service_account_file.return_value.project_id = "test-project"
        
        mock_bq_client_instance = mock_bq_client.return_value
        mock_bq_client_instance.query.return_value = MagicMock()
        mock_bq_client_instance.query.return_value.result.return_value = Mock()
        
        # Setup mock collection
        mock_collection = MagicMock()
        mock_chroma_instance = mock_chroma.return_value
        mock_chroma_instance.get_or_create_collection.return_value = mock_collection
        
        # Setup mock transformer
        mock_transformer_instance = mock_transformer.return_value
        mock_transformer_instance.encode.return_value = [0.1, 0.2, 0.3]
        
        # Create agent with mocks
        agent = SQLAgent(
            vanna_api_key="test_key",
            bigquery_credentials_path="test_path.json",
            vector_db_path="test_vector_db"
        )
        
        # Add mocks to agent for testing
        agent.mock_vanna = mock_vanna_instance
        agent.mock_bq_client = mock_bq_client_instance
        agent.mock_collection = mock_collection
        agent.mock_transformer = mock_transformer_instance
        
        yield agent

def test_agent_initialization(mock_agent):
    """Test that the agent initializes correctly"""
    assert mock_agent.vn is not None
    assert mock_agent.bq_client is not None
    assert mock_agent.collection is not None
    assert mock_agent.model is not None

def test_generate_sql(mock_agent):
    """Test SQL generation"""
    question = "Show me the top 10 records"
    
    # Mock find_similar_queries to return empty list
    with patch.object(mock_agent, 'find_similar_queries', return_value=[]):
        sql, similar = mock_agent.generate_sql(question)
        
        # Assert generate_sql was called correctly
        mock_agent.mock_vanna.generate_sql.assert_called_once_with(question=question)
        
        # Check result
        assert sql == "SELECT * FROM test_table LIMIT 10"
        assert similar == []

def test_generate_sql_with_examples(mock_agent):
    """Test SQL generation with example queries"""
    question = "Show me the top 10 records"
    
    # Mock similar queries that were successful
    similar_queries = [
        {
            "question": "Show me top records",
            "sql": "SELECT * FROM table LIMIT 5",
            "was_successful": True,
            "execution_time": 0.1
        }
    ]
    
    # Mock find_similar_queries to return our examples
    with patch.object(mock_agent, 'find_similar_queries', return_value=similar_queries):
        sql, similar = mock_agent.generate_sql(question)
        
        # Assert generate_sql was called with examples
        mock_agent.mock_vanna.generate_sql.assert_called_once()
        args, kwargs = mock_agent.mock_vanna.generate_sql.call_args
        
        # Check that examples were passed
        assert "examples" in kwargs
        assert len(kwargs["examples"]) == 1
        assert kwargs["examples"][0]["question"] == "Show me top records"
        
        # Check result
        assert sql == "SELECT * FROM test_table LIMIT 10"
        assert similar == similar_queries

def test_query_with_approval_required(mock_agent):
    """Test query method when approval is required but not provided"""
    question = "Show me sales data"
    
    # Mock generate_sql
    with patch.object(mock_agent, 'generate_sql', return_value=("SELECT * FROM sales", [])):
        result = mock_agent.query(
            question=question,
            require_approval=True,
            approved=False
        )
        
        # Check that query wasn't executed
        mock_agent.mock_bq_client.query.assert_not_called()
        
        # Check result structure
        assert result["question"] == question
        assert result["sql"] == "SELECT * FROM sales"
        assert result["requires_approval"] == True
        assert result["awaiting_approval"] == True
        assert result["was_successful"] is None

def test_query_with_approval_granted(mock_agent):
    """Test query method when approval is granted"""
    question = "Show me sales data"
    
    # Setup mock dataframe result
    mock_df = pd.DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})
    
    # Mock generate_sql and execute_query
    with patch.object(mock_agent, 'generate_sql', return_value=("SELECT * FROM sales", [])), \
         patch.object(mock_agent, 'execute_query', return_value=(Mock(), 0.5)), \
         patch.object(pd, 'DataFrame', return_value=mock_df), \
         patch.object(mock_agent, 'store_query_pair'):
        
        result = mock_agent.query(
            question=question,
            require_approval=True,
            approved=True
        )
        
        # Check that query was executed
        mock_agent.mock_bq_client.query.assert_called_once()
        
        # Check result structure
        assert result["question"] == question
        assert result["sql"] == "SELECT * FROM sales"
        assert result["requires_approval"] == True
        assert result["approved"] == True
        assert result["was_successful"] == True
        assert result["execution_time"] == 0.5
        assert "results" in result

def test_query_execution_error(mock_agent):
    """Test query method when execution raises an error"""
    question = "Show me sales data"
    
    # Mock generate_sql and make execute_query raise an exception
    with patch.object(mock_agent, 'generate_sql', return_value=("SELECT * FROM sales", [])), \
         patch.object(mock_agent, 'execute_query', side_effect=Exception("Query failed")), \
         patch.object(mock_agent, 'store_query_pair'):
        
        result = mock_agent.query(
            question=question,
            require_approval=False  # Skip approval
        )
        
        # Check result structure for error
        assert result["question"] == question
        assert result["sql"] == "SELECT * FROM sales"
        assert result["was_successful"] == False
        assert "error_message" in result
        assert result["error_message"] == "Query failed"