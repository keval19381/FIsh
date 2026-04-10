#!/usr/bin/env python3
"""
Script to check if an email exists in the database
"""
import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    print("ERROR: Supabase environment variables not found")
    exit(1)

# Initialize Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

email = "kevalshinde19381@gmail.com"

print(f"Checking if {email} exists in database...\n")

try:
    response = supabase.table("users").select("id, name, email, role, city").eq("email", email).execute()
    
    if response.data:
        user = response.data[0]
        print(f"✅ Found user: {user['name']}")
        print(f"   Email: {user['email']}")
        print(f"   Role: {user['role']}")
        print(f"   City: {user['city']}")
        print(f"   ID: {user['id']}")
    else:
        print(f"❌ Email {email} not found in database")
        
except Exception as e:
    print(f"❌ Error: {e}")
