from google.cloud import bigquery
from google.oauth2 import service_account
import os
import pandas as pd

def test_bigquery_connection():
    """Test a direct connection to BigQuery without using Vanna"""
    try:
        # Path to your service account key file
        key_path = "./sql-agent-project.json"
        print(f"Using credentials file: {os.path.abspath(key_path)}")
        
        if not os.path.exists(key_path):
            print(f"❌ Credentials file not found at: {key_path}")
            return False
        
        # Create credentials
        print("Creating credentials from service account file...")
        credentials = service_account.Credentials.from_service_account_file(
            key_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        
        # Create client
        print(f"Creating BigQuery client for project: {credentials.project_id}...")
        client = bigquery.Client(
            credentials=credentials,
            project=credentials.project_id,
        )
        
        # Test simple query
        print("\nRunning simple test query...")
        query = "SELECT 1 as test"
        query_job = client.query(query)
        results = query_job.result()
        
        for row in results:
            print(f"✅ Simple query successful! Test value: {row.test}")
        
        # Try to query the information schema
        print("\nQuerying INFORMATION_SCHEMA...")
        dataset_id = "sqlAgentTestv1"
        schema_query = f"""
        SELECT * 
        FROM {credentials.project_id}.INFORMATION_SCHEMA.SCHEMATA
        WHERE schema_name = '{dataset_id}'
        """
        
        schema_job = client.query(schema_query)
        schema_results = schema_job.result()
        schema_df = schema_results.to_dataframe()
        
        if len(schema_df) > 0:
            print(f"✅ Dataset '{dataset_id}' exists in project '{credentials.project_id}'")
            print(schema_df)
        else:
            print(f"❌ Dataset '{dataset_id}' does not exist in project '{credentials.project_id}'")
        
        # Try to list tables in the dataset
        print("\nListing tables in dataset...")
        tables_query = f"""
        SELECT table_name
        FROM {credentials.project_id}.{dataset_id}.INFORMATION_SCHEMA.TABLES
        """
        
        try:
            tables_job = client.query(tables_query)
            tables_results = tables_job.result()
            tables_df = tables_results.to_dataframe()
            
            if len(tables_df) > 0:
                print(f"✅ Found {len(tables_df)} tables in dataset '{dataset_id}':")
                for i, row in tables_df.iterrows():
                    print(f"  - {row['table_name']}")
            else:
                print(f"⚠️ No tables found in dataset '{dataset_id}'")
                
                # Try to create a test table
                print("\nAttempting to create a test table...")
                create_table_query = f"""
                CREATE TABLE IF NOT EXISTS {credentials.project_id}.{dataset_id}.test_table (
                    id INT64,
                    name STRING
                )
                """
                
                create_job = client.query(create_table_query)
                create_job.result()
                print(f"✅ Test table created in dataset '{dataset_id}'")
                
        except Exception as e:
            print(f"❌ Error listing tables: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

if __name__ == "__main__":
    print("Simple BigQuery Connection Test")
    print("==============================")
    test_bigquery_connection()