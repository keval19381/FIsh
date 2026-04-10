#!/usr/bin/env python3
"""
List ALL users in database
"""
import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

print("ALL USERS IN DATABASE:\n")

try:
    response = supabase.table("users").select("id, name, email, role").execute()
    
    if response.data:
        for user in response.data:
            print("- %s (ID: %s)" % (user['email'], user['id']))
            print("  Name: %s" % user['name'])
            print("  Role: %s\n" % user['role'])
    else:
        print("NO USERS FOUND")
        
except Exception as e:
    print("ERROR: %s" % str(e))
