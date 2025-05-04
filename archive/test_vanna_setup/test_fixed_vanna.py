import os
import json
import pandas as pd
from fixed_vanna import FullyFixedMyVanna

def load_config():
    """Load configuration from config.json file with environment variable overrides"""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {}
    
    # Convert keys to lowercase for consistency
    config = {k.lower(): v for k, v in config.items()}
    
    return config

def get_file_path(filename, subfolder=None):
    """Get the absolute path to a file, optionally in a subfolder"""
    if subfolder:
        return os.path.join(os.getcwd(), subfolder, filename)
    return os.path.join(os.getcwd(), filename)

def main():
    # Load configuration
    config = load_config()
    
    # Set absolute path for credentials
    credentials_path = os.path.abspath('./sql-agent-project.json')
    config['google_application_credentials'] = credentials_path
    
    # Print current working directory and check if credentials file exists
    print(f"Current working directory: {os.getcwd()}")
    print(f"Checking for credentials file at: {credentials_path}")
    if os.path.exists(credentials_path):
        print(f"✅ Credentials file exists")
    else:
        print(f"❌ Credentials file NOT found")
        return
    
    # Initialize Vanna with fully fixed class
    print("\nInitializing Fully Fixed Vanna with explicit credentials...")
    vn = FullyFixedMyVanna(config=config)
    
    # Connect to BigQuery
    project_id = config.get('bigquery_project_id')
    dataset_id = config.get('bigquery_dataset_id', config.get('default_dataset'))
    
    if not project_id:
        print("❌ BIGQUERY_PROJECT_ID is missing from config")
        return
    
    print(f"\nConnecting to BigQuery project '{project_id}', dataset '{dataset_id}'...")
    try:
        vn.connect_to_bigquery(
            project_id=project_id,
            dataset_id=dataset_id,
            credentials_path=credentials_path
        )
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return
    
    # Test direct SQL execution first
    print("\nTesting direct SQL execution...")
    try:
        sql_query = "SELECT 1 as test"
        print(f"Executing SQL: {sql_query}")
        result = vn.run_sql(sql_query)
        print("Query result:")
        print(result)
        print("✅ Direct SQL execution successful!")
    except Exception as e:
        print(f"❌ Direct SQL execution error: {e}")
        return
    
    # Define context folder path
    contexts_folder = 'contexts'
    
    # 1. Train with DDL
    ddl_path = get_file_path('custom_ddl.txt', contexts_folder)
    print(f"\nTraining with DDL from {ddl_path}...")
    try:
        with open(ddl_path, 'r') as f:
            ddl_content = f.read()
        vn.train(ddl=ddl_content)
        print("✅ DDL training complete")
    except FileNotFoundError:
        print(f"❌ File not found: {ddl_path}")
    except Exception as e:
        print(f"❌ Error training with DDL: {e}")
    
    # 2. Train with documentation
    doc_path = get_file_path('documentation.txt', contexts_folder)
    print(f"\nTraining with documentation from {doc_path}...")
    try:
        with open(doc_path, 'r') as f:
            doc_content = f.read()
        vn.train(documentation=doc_content)
        print("✅ Documentation training complete")
    except FileNotFoundError:
        print(f"❌ File not found: {doc_path}")
    except Exception as e:
        print(f"❌ Error training with documentation: {e}")
    
    # 3. Train with example question-SQL pairs
    examples_path = get_file_path('examples.json', contexts_folder)
    print(f"\nTraining with examples from {examples_path}...")
    try:
        with open(examples_path, 'r') as f:
            examples = json.load(f)
        for i, example in enumerate(examples):
            vn.train(
                question=example["question"],
                sql=example["sql"]
            )
            print(f"  Trained example {i+1}/{len(examples)}")
        print(f"✅ Example training complete. Added {len(examples)} question-SQL pairs")
    except FileNotFoundError:
        print(f"❌ File not found: {examples_path}")
    except Exception as e:
        print(f"❌ Error training with examples: {e}")
    
    # 4. Try to manually run a SQL query against the table
    print("\nTrying to query the groceries table...")
    try:
        query = f"SELECT * FROM {dataset_id}.groceries LIMIT 3"
        print(f"Executing SQL: {query}")
        results = vn.run_sql(query)
        if results is not None:
            print("Query results:")
            print(results)
            print("✅ Direct table query successful!")
        else:
            print("⚠️ No results returned")
    except Exception as e:
        print(f"❌ Error querying table: {e}")
    
    # 5. Verify training data
    print("\nVerifying training data...")
    try:
        training_data = vn.get_training_data()
        print(f"Total training items: {len(training_data)}")
        print("Types of training data:")
        print(training_data['type'].value_counts())
        print("✅ Training data verification successful!")
    except Exception as e:
        print(f"❌ Error retrieving training data: {e}")
    
    # 6. Test with a sample question
    print("\nTesting with a sample question...")
    try:
        question = "Show me 4 sample data points from the groceries table"
        print(f"Question: {question}")
        sql = vn.ask(question)
        print(f"Generated SQL: {sql}")
        
        # Check if we have stored results from the execution
        if hasattr(vn, '_last_results') and vn._last_results is not None:
            print("Query results:")
            print(vn._last_results)
            print("✅ Full question-to-results pipeline successful!")
        else:
            print("⚠️ No results stored from execution")
        
        print("✅ Question answering test complete")
    except Exception as e:
        print(f"❌ Error testing question answering: {e}")

if __name__ == "__main__":
    main()