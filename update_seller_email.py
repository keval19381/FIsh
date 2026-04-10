#!/usr/bin/env python3
"""
Script to update Keval's seller email from keval.seller@gmail.com to kevalshinde19381@gmail.com
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

old_email = "keval.seller@gmail.com"
new_email = "kevalshinde19381@gmail.com"

print(f"Updating seller email from {old_email} to {new_email}...\n")

try:
    # Check if old email exists
    existing = supabase.table("users").select("*").eq("email", old_email).execute()
    
    if not existing.data:
        print(f"⚠️  Seller with email {old_email} not found in database")
        exit(1)
    
    seller = existing.data[0]
    seller_id = seller["id"]
    seller_name = seller["name"]
    
    # Check if new email is already taken
    new_email_check = supabase.table("users").select("*").eq("email", new_email).execute()
    if new_email_check.data:
        print(f"❌ Email {new_email} is already in use!")
        exit(1)
    
    # Update the email
    response = supabase.table("users").update({"email": new_email}).eq("id", seller_id).execute()
    
    if response.data:
        print(f"✅ Email updated successfully!")
        print(f"\nSeller: {seller_name}")
        print(f"Old Email: {old_email}")
        print(f"New Email: {new_email}")
        print(f"Password: seller123")
        print(f"Role: seller")
        print(f"\nYou can now login with the new email address!")
    else:
        print(f"❌ Failed to update email")
        
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
