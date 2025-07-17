import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

# Initialize Supabase client
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(url, key)

def delete_all_home_data():
    tables_to_delete = [
        "home_content",
        "hero_images",
        "home_stats",
        "home_services"
    ]

    print("Deleting all data from home section tables...")

    for table_name in tables_to_delete:
        try:
            # Delete all rows from the current table
            # Using .neq('id', '0') is a common way to delete all rows safely
            # as '0' is unlikely to be a valid ID for any row (especially UUIDs).
            response = supabase.table(table_name).delete().gt('id', '0').execute()
            print(f"Successfully deleted data from {table_name}. Response: {response.data}")
        except Exception as e:
            print(f"Error deleting data from {table_name}: {e}")

if __name__ == "__main__":
    delete_all_home_data()
