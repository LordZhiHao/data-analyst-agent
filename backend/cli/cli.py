"""
Command-line interface for the Vanna SQL Agent.
Provides interactive and scripted query execution with approval flow.
"""

import argparse
import os
import json
import sys
import importlib
from pathlib import Path

# Add the parent directory to sys.path so we can import the app package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent import SQLAgent
from app.config import settings

def get_user_approval(sql):
    """Get user approval for SQL execution"""
    print("\n" + "-" * 80)
    print("Generated SQL Query:")
    print("-" * 80)
    print(sql)
    print("-" * 80)
    
    while True:
        response = input("\nDo you want to execute this SQL query? (y/yes/n/no): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please respond with 'y', 'yes', 'n', or 'no'.")

def display_results(results):
    """Display query results in a formatted way"""
    if not results:
        print("No results returned.")
        return
    
    # Get column widths
    columns = list(results[0].keys())
    col_widths = {col: max(len(str(row.get(col, ''))) for row in results + [{'col': col}]) for col in columns}
    
    # Print header
    header = " | ".join(f"{col:{col_widths[col]}}" for col in columns)
    print("-" * len(header))
    print(header)
    print("-" * len(header))
    
    # Print rows
    for row in results:
        print(" | ".join(f"{str(row.get(col, '')):{col_widths[col]}}" for col in columns))
    
    print("-" * len(header))
    print(f"Total rows: {len(results)}")

def format_duration(seconds):
    """Format execution time nicely"""
    if seconds < 1:
        return f"{seconds*1000:.2f} ms"
    elif seconds < 60:
        return f"{seconds:.2f} seconds"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes} min {secs:.2f} sec"

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Vanna SQL Agent Command Line Interface")
    parser.add_argument("--config", default="config.json", help="Path to configuration file")
    parser.add_argument("--dataset", help="BigQuery dataset to connect to")
    parser.add_argument("--question", help="Natural language question to query")
    parser.add_argument("--no-approval", action="store_true", help="Skip approval step")
    parser.add_argument("--history", action="store_true", help="View query history")
    parser.add_argument("--limit", type=int, default=10, help="Limit for history items")
    
    args = parser.parse_args()
    
    # Load configuration from file or environment
    try:
        # Try to load from file first
        if os.path.exists(args.config):
            with open(args.config, 'r') as f:
                config = json.load(f)
                
            # Initialize agent with file config
            agent = SQLAgent(
                vanna_api_key=config.get("vanna_api_key", settings.VANNA_API_KEY),
                bigquery_credentials_path=config.get("bigquery_credentials_path", settings.BIGQUERY_CREDENTIALS_PATH),
                vector_db_path=config.get("vector_db_path", settings.VECTOR_DB_PATH)
            )
            
            # Set default dataset from config file if not specified in args
            default_dataset = args.dataset or config.get("default_dataset", settings.DEFAULT_DATASET)
        else:
            # Use environment variables if no config file
            print(f"Config file not found: {args.config}, using environment variables")
            
            # Initialize agent with environment settings
            agent = SQLAgent(
                vanna_api_key=settings.VANNA_API_KEY,
                bigquery_credentials_path=settings.BIGQUERY_CREDENTIALS_PATH,
                vector_db_path=settings.VECTOR_DB_PATH
            )
            
            # Set default dataset from environment if not specified in args
            default_dataset = args.dataset or settings.DEFAULT_DATASET
            
            # Create default config file if it doesn't exist
            if not os.path.exists(args.config):
                default_config = {
                    "vanna_api_key": settings.VANNA_API_KEY,
                    "bigquery_credentials_path": settings.BIGQUERY_CREDENTIALS_PATH,
                    "vector_db_path": settings.VECTOR_DB_PATH,
                    "default_dataset": settings.DEFAULT_DATASET
                }
                with open(args.config, 'w') as f:
                    json.dump(default_config, f, indent=2)
                print(f"Created default config file at {args.config}")
            
    except Exception as e:
        print(f"Error initializing agent: {e}")
        return
    
    # Connect to dataset if specified
    if default_dataset:
        print(f"Connecting to BigQuery dataset: {default_dataset}")
        try:
            result = agent.connect_to_bigquery_schema(default_dataset)
            print(result)
        except Exception as e:
            print(f"Error connecting to dataset: {e}")
    
    # Display history
    if args.history:
        print(f"\nQuery History (last {args.limit} queries):")
        print("-" * 80)
        history = agent.get_query_history(limit=args.limit)
        for i, item in enumerate(history, 1):
            status = "✅ Success" if item["was_successful"] else "❌ Failed"
            print(f"{i}. {item['question']}")
            print(f"   Status: {status} | Time: {format_duration(item['execution_time'])} | {item['timestamp']}")
        return
    
    # Interactive mode if no question provided
    if not args.question:
        print("\nVanna SQL Agent CLI - Interactive Mode")
        print("Type 'exit' or 'quit' to exit, 'history' to view query history\n")
        
        while True:
            question = input("\nEnter your question: ").strip()
            
            if question.lower() in ['exit', 'quit']:
                break
            
            if question.lower() == 'history':
                history = agent.get_query_history(limit=args.limit)
                for i, item in enumerate(history, 1):
                    status = "✅ Success" if item["was_successful"] else "❌ Failed"
                    print(f"{i}. {item['question']}")
                    print(f"   Status: {status} | Time: {format_duration(item['execution_time'])}")
                continue
            
            if not question:
                continue
            
            # First, generate SQL without executing
            if not args.no_approval:
                # Get query without execution
                result = agent.query(
                    question=question, 
                    require_approval=True,
                    approved=False
                )
                
                # Ask for approval
                approved = get_user_approval(result["sql"])
                
                if not approved:
                    print("Query execution cancelled.")
                    continue
                
                # Execute the approved query
                result = agent.query(
                    question=question,
                    require_approval=True,
                    approved=True
                )
            else:
                # Skip approval flow
                result = agent.query(
                    question=question,
                    require_approval=False
                )
            
            # Display results
            if result["was_successful"]:
                print(f"\n✅ Query executed successfully in {format_duration(result['execution_time'])}")
                if "results" in result and result["results"] is not None:
                    print("\nResults:")
                    display_results(result["results"].to_dict(orient="records"))
                else:
                    print("No results returned.")
            else:
                print(f"\n❌ Query failed: {result.get('error_message', 'Unknown error')}")
    
    # Process single question
    else:
        # First, generate SQL without executing
        if not args.no_approval:
            # Get query without execution
            result = agent.query(
                question=args.question, 
                require_approval=True,
                approved=False
            )
            
            # Ask for approval
            approved = get_user_approval(result["sql"])
            
            if not approved:
                print("Query execution cancelled.")
                return
            
            # Execute the approved query
            result = agent.query(
                question=args.question,
                require_approval=True,
                approved=True
            )
        else:
            # Skip approval flow
            result = agent.query(
                question=args.question,
                require_approval=False
            )
        
        # Display results
        if result["was_successful"]:
            print(f"\n✅ Query executed successfully in {format_duration(result['execution_time'])}")
            if "results" in result and result["results"] is not None:
                print("\nResults:")
                display_results(result["results"].to_dict(orient="records"))
            else:
                print("No results returned.")
        else:
            print(f"\n❌ Query failed: {result.get('error_message', 'Unknown error')}")

if __name__ == "__main__":
    main()