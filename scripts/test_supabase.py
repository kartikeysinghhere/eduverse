"""Quick Supabase connection diagnostic."""
import os, sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

url = os.environ.get("SUPABASE_URL", "")
key = os.environ.get("SUPABASE_KEY", "")

print(f"SUPABASE_URL = {url}")
print(f"SUPABASE_KEY = {key[:20]}...{key[-6:]}" if len(key) > 26 else f"SUPABASE_KEY = {key}")

if not url or not key:
    print("ERROR: Missing Supabase credentials")
    sys.exit(1)

# Check URL format
if not url.startswith("https://") or ".supabase.co" not in url:
    print(f"WARNING: URL format looks suspicious: {url}")

# Check key format - Supabase anon keys are JWTs starting with 'eyJ'
if not key.startswith("eyJ"):
    print(f"ERROR: SUPABASE_KEY doesn't look like a valid Supabase JWT key!")
    print(f"  Supabase anon/service keys start with 'eyJ...'")
    print(f"  Your key starts with: '{key[:20]}'")
    print(f"  This is likely the root cause of connection failures.")
    sys.exit(1)

print("\nKey format looks valid. Attempting connection...")

try:
    from supabase import create_client
    import httpx
    from typing import cast, List, Dict, Any
    client = create_client(url, key)
    response = client.table("users").select("id, username, role").execute()
    users = cast(List[Dict[str, Any]], response.data)
    print(f"SUCCESS! Found {len(users)} users:")
    for u in users:
        print(f"  - {u['username']} (role: {u['role']}, id: {u['id']})")
except Exception as e:
    print(f"Connection failed: {type(e).__name__}: {e}")
    sys.exit(1)
