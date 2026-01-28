#!/usr/bin/env python3
"""
Create Test User Script
Creates a test user in Keycloak for testing user management features

Usage:
    python create_test_user.py
    python create_test_user.py --email test@example.com --username testuser
    python create_test_user.py --role admin --tier professional
"""

import asyncio
import argparse
import sys
import os
from datetime import datetime

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from keycloak_integration import (
    create_user,
    set_user_password,
    assign_realm_role_to_user,
    get_user_by_email,
    KEYCLOAK_URL,
    KEYCLOAK_REALM
)


async def create_test_user(
    email: str,
    username: str,
    first_name: str,
    last_name: str,
    password: str,
    tier: str = "trial",
    role: str = None,
    email_verified: bool = True
):
    """
    Create a test user in Keycloak
    
    Args:
        email: User email address
        username: Username
        first_name: First name
        last_name: Last name
        password: User password
        tier: Subscription tier (trial, starter, professional, enterprise)
        role: Optional realm role to assign
        email_verified: Whether email is verified
    """
    print(f"\n{'='*60}")
    print(f"Creating Test User in Keycloak")
    print(f"{'='*60}")
    print(f"Keycloak URL: {KEYCLOAK_URL}")
    print(f"Realm: {KEYCLOAK_REALM}")
    print(f"{'='*60}\n")
    
    # Check if user already exists
    print(f"1. Checking if user already exists...")
    existing_user = await get_user_by_email(email)
    if existing_user:
        print(f"   ❌ User with email {email} already exists!")
        print(f"   User ID: {existing_user.get('id')}")
        print(f"   Username: {existing_user.get('username')}")
        return False
    print(f"   ✓ User does not exist, proceeding with creation\n")
    
    # Create user attributes
    attributes = {
        "subscription_tier": [tier],
        "subscription_status": ["active"],
        "api_calls_limit": ["1000"],
        "api_calls_used": ["0"],
        "api_calls_reset_date": [datetime.utcnow().date().isoformat()],
        "created_via": ["test_script"],
        "test_user": ["true"]
    }
    
    # Create user in Keycloak
    print(f"2. Creating user in Keycloak...")
    print(f"   Email: {email}")
    print(f"   Username: {username}")
    print(f"   Name: {first_name} {last_name}")
    print(f"   Tier: {tier}")
    print(f"   Email Verified: {email_verified}")
    
    user_id = await create_user(
        email=email,
        username=username,
        first_name=first_name,
        last_name=last_name,
        attributes=attributes,
        email_verified=email_verified
    )
    
    if not user_id:
        print(f"   ❌ Failed to create user in Keycloak")
        return False
    
    print(f"   ✓ User created successfully!")
    print(f"   User ID: {user_id}\n")
    
    # Set password
    print(f"3. Setting user password...")
    password_set = await set_user_password(user_id, password, temporary=False)
    
    if not password_set:
        print(f"   ❌ Failed to set password (user created but without password)")
    else:
        print(f"   ✓ Password set successfully\n")
    
    # Assign role if specified
    if role:
        print(f"4. Assigning realm role '{role}'...")
        role_assigned = await assign_realm_role_to_user(user_id, role)
        
        if not role_assigned:
            print(f"   ❌ Failed to assign role '{role}'")
            print(f"   Note: Role may not exist in Keycloak realm")
        else:
            print(f"   ✓ Role '{role}' assigned successfully\n")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"✅ Test User Created Successfully!")
    print(f"{'='*60}")
    print(f"User ID:       {user_id}")
    print(f"Email:         {email}")
    print(f"Username:      {username}")
    print(f"Password:      {password}")
    print(f"Tier:          {tier}")
    print(f"Role:          {role or 'None'}")
    print(f"Email Verified: {email_verified}")
    print(f"{'='*60}")
    print(f"\nYou can now login with:")
    print(f"  Email/Username: {email} or {username}")
    print(f"  Password: {password}")
    print(f"\nAccess user management at:")
    print(f"  https://your-domain.com/admin/system/users")
    print(f"{'='*60}\n")
    
    return True


def main():
    """Main function to parse arguments and create test user"""
    parser = argparse.ArgumentParser(
        description="Create a test user in Keycloak for user management testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create basic test user with defaults
  python create_test_user.py
  
  # Create user with custom email and username
  python create_test_user.py --email john@example.com --username johndoe
  
  # Create admin user with professional tier
  python create_test_user.py --email admin@test.com --username admin --role admin --tier professional
  
  # Create user with custom name and password
  python create_test_user.py --first-name "John" --last-name "Doe" --password "SecurePass123!"
  
Available tiers: trial, starter, professional, enterprise
Available roles: Check your Keycloak realm roles (common: admin, user, moderator)
        """
    )
    
    # User details
    parser.add_argument(
        '--email',
        default=f'testuser-{datetime.now().strftime("%Y%m%d-%H%M%S")}@example.com',
        help='User email address (default: auto-generated)'
    )
    parser.add_argument(
        '--username',
        default=f'testuser-{datetime.now().strftime("%Y%m%d-%H%M%S")}',
        help='Username (default: auto-generated)'
    )
    parser.add_argument(
        '--first-name',
        default='Test',
        help='First name (default: Test)'
    )
    parser.add_argument(
        '--last-name',
        default='User',
        help='Last name (default: User)'
    )
    parser.add_argument(
        '--password',
        default='TestPassword123!',
        help='User password (default: TestPassword123!)'
    )
    
    # Subscription and role
    parser.add_argument(
        '--tier',
        choices=['trial', 'starter', 'professional', 'enterprise'],
        default='trial',
        help='Subscription tier (default: trial)'
    )
    parser.add_argument(
        '--role',
        help='Realm role to assign (optional, e.g., admin, user, moderator)'
    )
    parser.add_argument(
        '--email-verified',
        action='store_true',
        default=True,
        help='Mark email as verified (default: True)'
    )
    parser.add_argument(
        '--email-not-verified',
        action='store_true',
        help='Mark email as NOT verified'
    )
    
    args = parser.parse_args()
    
    # Handle email verification flag
    email_verified = not args.email_not_verified
    
    # Run async function
    success = asyncio.run(create_test_user(
        email=args.email,
        username=args.username,
        first_name=args.first_name,
        last_name=args.last_name,
        password=args.password,
        tier=args.tier,
        role=args.role,
        email_verified=email_verified
    ))
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
