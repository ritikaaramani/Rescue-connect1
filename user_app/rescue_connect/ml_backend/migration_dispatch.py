import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")

if not url or not key:
    print("Error: Missing Supabase credentials")
    exit(1)

supabase: Client = create_client(url, key)

print("🚀 Starting Database Migration for Dispatch System...")

# SQL to add new columns
sql_commands = [
    """
    ALTER TABLE posts 
    ADD COLUMN IF NOT EXISTS dispatch_status TEXT DEFAULT 'pending';
    """,
    """
    ALTER TABLE posts 
    ADD COLUMN IF NOT EXISTS assigned_team TEXT;
    """
]

for sql in sql_commands:
    try:
        # We use the 'rpc' hack or just direct execution if enabled, 
        # but supabase-py client often forbids direct SQL.
        # However, we can use the postgrest client usually?
        # Actually, standard supabase client doesn't support raw SQL easily without RPC.
        # But wait, looking at my previous work, I didn't verify if I can run raw SQL.
        # If I can't, I might need to ask the user to run it in Supabase Dashboard.
        
        # Let's try a workaround: using a dummy select to check connection
        # But to alter table, I really need SQL editor access usually.
        # UNLESS I have a stored procedure (RPC) for executing SQL. Be we don't.
        
        # Alternative: We can try to assume the columns exist or handle errors in the code?
        # No, the frontend will fail if it tries to read them.
        
        # Let's try to just print the SQL for the user?
        # OR better: The user has a `sql` folder in `ml_backend`.
        pass
    except Exception as e:
        print(f"Error: {e}")

print("⚠️  AUTO-MIGRATION VIA PYTHON CLIENT IS OFTEN RESTRICTED.")
print("⚠️  Please run the following SQL in your Supabase SQL Editor:")
print("\n" + "\n".join(sql_commands) + "\n")
