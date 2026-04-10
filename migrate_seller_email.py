#!/usr/bin/env python3
"""
Update seller email by deleting old entry and creating new one
"""
import os
import hashlib
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    print("ERROR: Supabase environment variables not found")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

old_email = "keval.seller@gmail.com"
new_email = "kevalshinde19381@gmail.com"

print("Step 1: Looking for seller with old email: %s" % old_email)

try:
    # Find the seller
    response = supabase.table("users").select("id, name, password_hash, role, city").eq("email", old_email).execute()
    
    if not response.data:
        print("ERROR: Seller not found with email %s" % old_email)
        exit(1)
    
    seller = response.data[0]
    seller_id = seller['id']
    seller_name = seller['name']
    print("FOUND: %s (ID: %s)" % (seller_name, seller_id))
    
    print("\nStep 2: Deleting old entry...")
    supabase.table("users").delete().eq("id", seller_id).execute()
    print("DELETED")
    
    print("\nStep 3: Creating new seller with updated email...")
    new_seller = supabase.table("users").insert({
        "name": seller_name,
        "email": new_email,
        "password_hash": seller['password_hash'],
        "role": seller['role'],
        "city": seller['city'],
        "email_verified": True
    }).execute()
    
    if new_seller.data:
        print("CREATED: %s with email %s" % (seller_name, new_email))
        print("\nSUCCESS! Seller email updated.")
        print("\nNew Login Credentials:")
        print("Email: %s" % new_email)
        print("Password: seller123")
        print("Role: seller")
    else:
        print("ERROR: Could not create new seller entry")
        
except Exception as e:
    print("ERROR: %s" % str(e))
    import traceback
    traceback.print_exc()
