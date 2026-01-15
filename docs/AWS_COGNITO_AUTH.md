# AWS Cognito Authentication

## Overview

The Yoto Smart Stream application now supports AWS Cognito User Pools for authentication when deployed on AWS. This provides a managed authentication service with features like:

- Secure password management
- Multi-factor authentication (optional)
- Password reset flows
- Account recovery
- Email verification
- Federated identity (optional)

## Architecture

When deployed to AWS, the application uses a hybrid authentication approach:

1. **AWS Cognito** (Primary on AWS):
   - User authentication and management
   - Secure token-based auth
   - Password policies and MFA
   
2. **Local Database** (Fallback):
   - SQLite authentication when Cognito is not available
   - Used for local development
   - Backwards compatible

## Automatic Detection

The application automatically detects if it's running on AWS by checking for the `COGNITO_USER_POOL_ID` environment variable. When present, Cognito authentication is used; otherwise, it falls back to local SQLite-based authentication.

```python
USE_COGNITO = os.getenv("COGNITO_USER_POOL_ID") is not None
```

## Cognito Resources Created

The CDK stack creates the following Cognito resources:

### User Pool
- **Name**: `yoto-users-{environment}`
- **Sign-in**: Username or email
- **Auto-verify**: Email
- **Password Policy**:
  - Minimum 8 characters
  - Requires: uppercase, lowercase, digits
  - Symbols optional

### User Pool Client
- **Name**: `yoto-webapp-{environment}`
- **Auth Flows**: 
  - USER_PASSWORD_AUTH
  - USER_SRP_AUTH (Secure Remote Password)
- **OAuth Scopes**: email, openid, profile

### Hosted UI Domain
- **Domain**: `yoto-smart-stream-{environment}.auth.{region}.amazoncognito.com`
- Provides built-in login/signup pages

## Usage

### Creating Users

Users can be created through the admin API when authenticated as an admin:

```bash
curl -X POST https://your-api.execute-api.us-east-1.amazonaws.com/api/admin/users \
  -H "Content-Type: application/json" \
  -H "Cookie: session=your-session-token" \
  -d '{
    "username": "newuser",
    "email": "user@example.com",
    "password": "SecurePass123"
  }'
```

This creates the user in both:
1. AWS Cognito (if enabled)
2. Local database (for backwards compatibility)

### Authentication Flow

1. User submits username and password to `/api/user/login`
2. If Cognito is enabled:
   - Authenticate with Cognito using `AdminInitiateAuth`
   - On success, create session JWT token
   - Store session in HTTP-only cookie
3. If Cognito fails or is disabled:
   - Fall back to local database authentication
   - Verify password hash with Argon2
   - Create session JWT token

### Session Management

After successful authentication, a session JWT token is created and stored in an HTTP-only cookie. This token is used for all subsequent requests to authenticate the user.

## CDK Configuration

### Stack Outputs

After deployment, the following Cognito information is available:

```bash
aws cloudformation describe-stacks \
  --stack-name YotoSmartStream-dev \
  --query 'Stacks[0].Outputs'
```

Outputs include:
- `UserPoolId`: Cognito User Pool ID
- `UserPoolClientId`: App client ID
- `CognitoLoginUrl`: Hosted UI login URL

### Environment Variables

The Lambda function automatically receives:
- `COGNITO_USER_POOL_ID`: User pool identifier
- `COGNITO_CLIENT_ID`: App client identifier

### IAM Permissions

The Lambda execution role is granted the following Cognito permissions:
- `cognito-idp:AdminInitiateAuth` - Authenticate users
- `cognito-idp:AdminCreateUser` - Create new users
- `cognito-idp:AdminSetUserPassword` - Set user passwords
- `cognito-idp:AdminGetUser` - Get user details
- `cognito-idp:ListUsers` - List all users

## Local Development

For local development without AWS, the application automatically falls back to SQLite-based authentication:

```bash
# No COGNITO_USER_POOL_ID set
export DATABASE_URL="sqlite:///./yoto_smart_stream.db"

# Start the application
python -m yoto_smart_stream
```

Users created locally use Argon2 password hashing and are stored in the SQLite database.

## Migration

### Existing Users

Existing users in the SQLite database will continue to work:
- When deployed to AWS, they remain in the local database
- Can authenticate using the fallback authentication flow
- Admin can migrate users to Cognito by creating them through the API

### Migration Script

To migrate existing users to Cognito:

```python
import boto3
from yoto_smart_stream.database import SessionLocal
from yoto_smart_stream.models import User

cognito = boto3.client('cognito-idp')
user_pool_id = "your-pool-id"

db = SessionLocal()
users = db.query(User).all()

for user in users:
    try:
        cognito.admin_create_user(
            UserPoolId=user_pool_id,
            Username=user.username,
            UserAttributes=[
                {'Name': 'email', 'Value': user.email or f"{user.username}@example.com"},
                {'Name': 'email_verified', 'Value': 'true'}
            ],
            MessageAction='SUPPRESS'
        )
        print(f"✓ Migrated: {user.username}")
    except Exception as e:
        print(f"✗ Failed to migrate {user.username}: {e}")
```

## Security Considerations

### Password Security
- Cognito uses industry-standard encryption for passwords
- Passwords never stored in plaintext
- Local fallback uses Argon2 password hashing

### Token Security
- Cognito tokens are short-lived (1 hour by default)
- Refresh tokens can be configured for longer sessions
- Session cookies are HTTP-only to prevent XSS attacks

### Best Practices
1. Enable MFA for admin users
2. Use strong password policies
3. Enable email verification
4. Monitor failed login attempts
5. Regularly review user access

## Troubleshooting

### Authentication Fails
```bash
# Check if Cognito is enabled
echo $COGNITO_USER_POOL_ID

# View Lambda logs
aws logs tail /aws/lambda/yoto-api-dev --follow

# Test Cognito directly
aws cognito-idp admin-initiate-auth \
  --user-pool-id your-pool-id \
  --client-id your-client-id \
  --auth-flow ADMIN_NO_SRP_AUTH \
  --auth-parameters USERNAME=admin,PASSWORD=yourpassword
```

### User Creation Fails
```bash
# Check Lambda IAM permissions
aws iam get-role-policy \
  --role-name YotoSmartStream-dev-LambdaRole \
  --policy-name cognito-policy

# List existing users
aws cognito-idp list-users --user-pool-id your-pool-id
```

### Cognito Not Available
If Cognito is not working, the application automatically falls back to local database authentication. Check:
1. `COGNITO_USER_POOL_ID` environment variable is set
2. Lambda has proper IAM permissions
3. User pool exists and is active

## Cost

AWS Cognito pricing (as of 2024):
- **Free Tier**: 50,000 MAU (Monthly Active Users)
- **After Free Tier**: $0.00550 per MAU

For home use with < 10 users, Cognito is effectively **free**.

## References

- [AWS Cognito Documentation](https://docs.aws.amazon.com/cognito/)
- [Cognito User Pools](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-identity-pools.html)
- [CDK Cognito Constructs](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_cognito-readme.html)
