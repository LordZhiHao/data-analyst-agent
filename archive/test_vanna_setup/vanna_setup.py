import os
import json
import pandas as pd
from my_vanna_module import MyVanna

def load_config():
    """Load configuration from config.json file with environment variable overrides"""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {}
    
    # Convert keys to lowercase for consistency
    config = {k.lower(): v for k, v in config.items()}
    
    # Override with environment variables if they exist
    for key in config:
        env_value = os.environ.get(key.upper())
        if env_value:
            config[key] = env_value
    
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
    print(f"Using credentials file: {credentials_path}")
    if os.path.exists(credentials_path):
        print(f"✅ Credentials file exists")
    else:
        print(f"❌ Credentials file NOT found")
        return
    
    # Initialize Vanna
    print("\nInitializing Vanna with MongoDB and Gemini...")
    vn = MyVanna(config=config)
    
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
    
    # 4. Try to get information schema
    print("\nAttempting to retrieve BigQuery information schema...")
    try:
        query = f"""
        SELECT * 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = '{dataset_id}'
        LIMIT 10
        """
        df_information_schema = vn.run_sql(query)
        
        if df_information_schema is not None and len(df_information_schema) > 0:
            print(f"Retrieved {len(df_information_schema)} columns from information schema")
            print("Sample schema information:")
            print(df_information_schema[['TABLE_NAME', 'COLUMN_NAME', 'DATA_TYPE']].head())
            
            print("\nGenerating training plan from schema...")
            plan = vn.get_training_plan_generic(df_information_schema)
            print(f"Generated training plan with {len(plan)} items")
            
            print("Executing training plan...")
            vn.train(plan=plan)
            print("✅ Schema-based training complete")
        else:
            print("⚠️ Information schema returned no results")
    except Exception as e:
        print(f"❌ Could not retrieve information schema: {e}")
    
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
        question = "What is the average membership fee for Gold tier customers?"
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
        
    except Exception as e:
        print(f"❌ Error testing question answering: {e}")
    
    # 7. Launch the web interface (optional)
    should_launch_web = config.get('launch_web_ui', 'false').lower() == 'true'
    
    if should_launch_web:
        print("\nLaunching web interface...")
        try:
            from vanna.flask import VannaFlaskApp
            app = VannaFlaskApp(vn)
            host = os.environ.get('WEB_HOST', '0.0.0.0')
            port = int(os.environ.get('WEB_PORT', '5000'))
            app.run(host=host, port=port)
        except Exception as e:
            print(f"❌ Error launching web interface: {e}")
    else:
        print("\nSetup complete! To launch the web interface, set LAUNCH_WEB_UI=true in config.json")

if __name__ == "__main__":
    main()