#!/usr/bin/env python3
"""
Script to add demo seller accounts to Supabase
"""
import os
import hashlib
from datetime import datetime
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

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Demo sellers to add
demo_sellers = [
    {
        "name": "Keval's Fresh Fish",
        "email": "kevalshinde19381@gmail.com",
        "password": "seller123",
        "city": "Mumbai",
    },
    {
        "name": "Mumbai Fish Market",
        "email": "mumbai.fish@gmail.com",
        "password": "seller456",
        "city": "Mumbai",
    },
    {
        "name": "Premium Seafood Co",
        "email": "premium.seafood@gmail.com",
        "password": "seller789",
        "city": "Bangalore",
    },
]

print("Adding demo sellers to Supabase...\n")

for seller in demo_sellers:
    try:
        # Check if seller already exists
        existing = supabase.table("users").select("*").eq("email", seller["email"]).execute()
        
        if existing.data:
            print(f"⚠️  Seller already exists: {seller['email']}")
            continue
        
        # Add new seller
        response = supabase.table("users").insert({
            "name": seller["name"],
            "email": seller["email"],
            "password_hash": hash_password(seller["password"]),
            "role": "seller",
            "city": seller["city"],
            "email_verified": True,  # Pre-verify demo accounts
            "created_at": datetime.now().isoformat()
        }).execute()
        
        if response.data:
            print(f"✅ Added seller: {seller['name']}")
            print(f"   Email: {seller['email']}")
            print(f"   Password: {seller['password']}")
            print()
        else:
            print(f"❌ Failed to add seller: {seller['email']}")
            print()
            
    except Exception as e:
        print(f"❌ Error adding seller {seller['email']}: {e}")
        print()

print("\n" + "="*50)
print("DEMO SELLERS CREDENTIALS")
print("="*50)

for seller in demo_sellers:
    print(f"\nSeller: {seller['name']}")
    print(f"Email: {seller['email']}")
    print(f"Password: {seller['password']}")
    print(f"Role: seller")
    print(f"City: {seller['city']}")

print("\n" + "="*50)
print("Done! You can now log in with these accounts.")
print("="*50)
