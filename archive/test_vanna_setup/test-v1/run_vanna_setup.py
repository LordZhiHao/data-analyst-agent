#!/usr/bin/env python3
"""
Run script for setting up Vanna AI with Grocery dataset
This script loads your files and initializes the Vanna AI setup.
"""

import os
import json
from vanna_grocery_setup import VannaGrocerySetup

def main():
    # Check for environment variables
    required_vars = ["GOOGLE_API_KEY", "MONGO_CONNECTION_STRING", "MONGO_DB_NAME", "MONGO_COLLECTION_NAME", "BIGQUERY_PROJECT_ID"]
    missing = [var for var in required_vars if not os.environ.get(var)]
    
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}")
        print("Please set these variables before running the script.")
        print("Example:")
        print('export GOOGLE_API_KEY="your_gemini_api_key"')
        print('export MONGO_CONNECTION_STRING="mongodb+srv://username:password@cluster.mongodb.net/"')
        print('export MONGO_DB_NAME="your_database_name"')
        print('export MONGO_COLLECTION_NAME="your_vector_collection_name"')
        print('export BIGQUERY_PROJECT_ID="your-gcp-project-id"')
        print('export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json" # Optional')
        return

    print("Setting up Vanna AI with your grocery dataset...")
    
    # Read your uploaded files
    with open('custom_ddl.txt', 'r') as f:
        ddl_content = f.read()
        
    with open('documentation.txt', 'r') as f:
        documentation_content = f.read()
        
    with open('examples.json', 'r') as f:
        examples_content = f.read()
    
    # Initialize the VannaGrocerySetup class
    vanna_setup = VannaGrocerySetup(
        # You can override environment variables here if needed
        # google_api_key="your_key_here",
        # mongo_connection_string="your_connection_string",
        # mongo_db_name="your_database",  
        # mongo_collection_name="your_collection",
        # bigquery_project_id="your_project_id",
        create_vector_index=True,  # This enables vector index creation for schema
        vector_dimension=1536  # Use 1536 for embedding-001 model
    )
    
    # Use the setup method
    vanna = vanna_setup.setup_from_files(
        ddl_content=ddl_content,
        documentation_content=documentation_content,
        examples_content=examples_content,
        model="gemini-pro"
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
            result, sql = vanna.ask_with_vector_enhancement(question)
            print("\nGenerated SQL:")
            print(sql)
            print("\nResult:")
            print(result)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()