"""
Migrate data from SQLite to DynamoDB
Run this after deploying the AWS stack
"""
import os
import sys
import sqlite3
from datetime import datetime, timezone

import boto3

# Configuration
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
DYNAMODB_TABLE = os.getenv('DYNAMODB_TABLE')
SQLITE_DB = os.getenv('SQLITE_DB', '../../yoto_smart_stream.db')

if not DYNAMODB_TABLE:
    print("Error: DYNAMODB_TABLE environment variable is required")
    print("Usage: DYNAMODB_TABLE=yoto-smart-stream-dev python migrate_to_dynamodb.py")
    sys.exit(1)

print(f"Migrating from SQLite ({SQLITE_DB}) to DynamoDB ({DYNAMODB_TABLE})")

# Connect to SQLite
try:
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_cursor = sqlite_conn.cursor()
    print("✓ Connected to SQLite database")
except Exception as e:
    print(f"✗ Error connecting to SQLite: {e}")
    sys.exit(1)

# Connect to DynamoDB
try:
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    table = dynamodb.Table(DYNAMODB_TABLE)
    print(f"✓ Connected to DynamoDB table: {DYNAMODB_TABLE}")
except Exception as e:
    print(f"✗ Error connecting to DynamoDB: {e}")
    sys.exit(1)

# Migrate users
print("\nMigrating users...")
try:
    sqlite_cursor.execute("SELECT * FROM users")
    users = sqlite_cursor.fetchall()
    
    for user in users:
        user_id, username, hashed_password, email, is_active, is_admin, yoto_refresh_token = user
        
        item = {
            'PK': f'USER#{username}',
            'SK': 'PROFILE',
            'user_id': user_id,
            'username': username,
            'hashed_password': hashed_password,
            'email': email or '',
            'is_active': bool(is_active),
            'is_admin': bool(is_admin),
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        
        # Add Yoto tokens if present
        if yoto_refresh_token:
            item['yoto_refresh_token'] = yoto_refresh_token
        
        table.put_item(Item=item)
        print(f"  ✓ Migrated user: {username}")
    
    print(f"✓ Migrated {len(users)} users")
    
except Exception as e:
    print(f"✗ Error migrating users: {e}")

# Close connections
sqlite_conn.close()
print("\n✓ Migration complete!")
print("\nNext steps:")
print("1. Verify data in DynamoDB using AWS Console")
print("2. Test the application with the new DynamoDB backend")
print("3. Once verified, you can backup and remove the SQLite database")
