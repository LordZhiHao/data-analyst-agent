from google.cloud import bigquery
import os
import json

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

def test_bigquery_connection():
    # Load config
    config = load_config()
    
    # Print credential information for debugging
    credentials_path = config.get('google_application_credentials')
    print(f"Credentials path from config: {credentials_path}")
    
    env_credentials = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    print(f"Credentials path from environment: {env_credentials}")
    
    # Check if file exists
    if credentials_path and os.path.exists(credentials_path):
        print(f"Credentials file exists at: {credentials_path}")
    else:
        print(f"WARNING: Credentials file not found at: {credentials_path}")
    
    # If necessary, explicitly set credentials path from config
    if credentials_path:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    
    try:
        # Create a client
        print("Creating BigQuery client...")
        client = bigquery.Client()
        
        # Test query
        print("Running test query...")
        query = "SELECT 1 as test"
        query_job = client.query(query)
        results = query_job.result()
        
        # Print results
        for row in results:
            print(f"Query success! Test value: {row.test}")
        
        return True
    except Exception as e:
        print(f"Connection error: {e}")
        return False

if __name__ == "__main__":
    print("Testing BigQuery connection...")
    test_bigquery_connection()