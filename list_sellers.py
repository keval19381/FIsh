#!/usr/bin/env python3
"""
Script to list all seller accounts
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

print("📋 All Seller Accounts in Database:\n")
print("="*70)

try:
    response = supabase.table("users").select("id, name, email, role, city").eq("role", "seller").execute()
    
    if response.data:
        for idx, seller in enumerate(response.data, 1):
            print(f"\n{idx}. {seller['name']}")
            print(f"   Email: {seller['email']}")
            print(f"   City: {seller['city']}")
            print(f"   ID: {seller['id']}")
    else:
        print("No sellers found")
        
except Exception as e:
    print(f"❌ Error: {e}")
