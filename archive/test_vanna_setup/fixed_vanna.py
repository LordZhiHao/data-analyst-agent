import os
import pandas as pd
from my_vanna_module import MyVanna as OriginalMyVanna
from google.oauth2 import service_account
from google.cloud import bigquery

class FullyFixedMyVanna(OriginalMyVanna):
    def __init__(self, config=None):
        # Initialize the parent
        super().__init__(config)
        
        # Immediately set up the run_sql method to avoid issues
        self._has_initialized_run_sql = False
    
    def connect_to_bigquery(self, project_id, dataset_id, credentials_path=None):
        """Override connect_to_bigquery to use explicit credentials"""
        if credentials_path is None:
            credentials_path = self.config.get('google_application_credentials', 
                                            './sql-agent-project.json')
        
        print(f"Using credentials file: {credentials_path}")
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(f"Credentials file not found at: {credentials_path}")
        
        try:
            # Create explicit credentials
            print("Creating explicit credentials from service account file...")
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            
            # Create client with explicit credentials
            print(f"Creating BigQuery client for project: {project_id}...")
            self.client = bigquery.Client(
                credentials=credentials,
                project=project_id,
            )
            
            # Test connection with simple query
            print("Testing connection with a simple query...")
            query_job = self.client.query("SELECT 1 as test")
            results = query_job.result()
            for row in results:
                print(f"Connection test successful! Test value: {row.test}")
            
            self.project_id = project_id
            self.dataset_id = dataset_id
            
            # Store these for later use
            self._bigquery_client = self.client
            self._bigquery_project_id = project_id
            self._bigquery_dataset_id = dataset_id
            
            # Set the run_sql method to use our BigQuery client
            self._setup_run_sql_method()
            
            print(f"Successfully connected to BigQuery project '{project_id}', dataset '{dataset_id}'")
            return self
            
        except Exception as e:
            print(f"Error connecting to BigQuery: {e}")
            print(f"Error type: {type(e).__name__}")
            raise
    
    def _setup_run_sql_method(self):
        """Setup the run_sql method to use our BigQuery client"""
        self._has_initialized_run_sql = True
        
        def run_sql_bigquery(sql):
            """Run SQL query on BigQuery"""
            try:
                # Check if we have a client
                if not hasattr(self, '_bigquery_client') or self._bigquery_client is None:
                    raise ValueError("BigQuery client not initialized. Call connect_to_bigquery first.")
                
                print(f"Executing SQL query: {sql}")
                query_job = self._bigquery_client.query(sql)
                results = query_job.result()
                
                # Convert to pandas DataFrame
                df = results.to_dataframe()
                print(f"Query executed successfully! Rows returned: {len(df)}")
                return df
            except Exception as e:
                print(f"Error executing SQL query: {e}")
                raise
        
        # Set the run_sql method
        self.run_sql = run_sql_bigquery
    
    def ask(self, question, **kwargs):
        """Override ask method to ensure run_sql is set up"""
        try:
            # Make sure run_sql is set up
            if not hasattr(self, '_has_initialized_run_sql') or not self._has_initialized_run_sql:
                self._setup_run_sql_method()
            
            # Get the SQL generated for the question
            sql = super().generate_sql(question, **kwargs)
            print(f"Generated SQL: {sql}")
            
            # Try to run the SQL
            try:
                if sql:
                    print("Executing generated SQL...")
                    results = self.run_sql(sql)
                    print(f"SQL execution successful! Rows returned: {len(results)}")
                    
                    # Store results for reference
                    self._last_results = results
                else:
                    print("No SQL was generated.")
            except Exception as e:
                print(f"Error executing generated SQL: {e}")
            
            # Return the generated SQL as normal
            return sql
                
        except Exception as e:
            print(f"Error in ask method: {e}")
            # Still return something even on error
            return f"Error: {str(e)}"