#!/usr/bin/env python3
"""
Script to update Keval's seller email
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

print("Updating seller email from %s to %s...\n" % (old_email, new_email))

try:
    # Update the email
    response = supabase.table("users").update({"email": new_email}).eq("email", old_email).execute()
    
    if response.data:
        print("Email updated successfully!")
        seller = response.data[0]
        print("\nSeller: %s" % seller.get('name', 'N/A'))
        print("Old Email: %s" % old_email)
        print("New Email: %s" % new_email)
        print("Password: seller123")
        print("Role: seller")
        print("\nYou can now login with the new email address!")
    else:
        print("No seller found with email: %s" % old_email)
        
except Exception as e:
    print("Error: %s" % str(e))
    import traceback
    traceback.print_exc()
