"""
AWS Lambda handler for Yoto Smart Stream API
Uses Mangum to adapt FastAPI for Lambda
"""
import os
import sys

# Add parent directory to path to import yoto_smart_stream
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mangum import Mangum

# Import the FastAPI app
# Note: This assumes the yoto_smart_stream package is copied to the Lambda package
try:
    from yoto_smart_stream.api.app import create_app
    from yoto_smart_stream.database import init_db
    from yoto_smart_stream.database import SessionLocal
    from yoto_smart_stream.models import User
    from yoto_smart_stream.auth import get_password_hash
    import logging
    
    # Configure logging first
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Initialize database on cold start
    print("Lambda: Initializing database...")  # Print to ensure output
    logger.info("Initializing database for Lambda...")
    init_db()
    print("Lambda: Database initialized")
    
    # Create default admin user if doesn't exist  
    db = SessionLocal()
    try:
        print("Lambda: Checking for admin user...")
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            print("Lambda: Creating admin user...")
            hashed = get_password_hash("yoto")
            admin_user = User(
                username="admin",
                email="admin@yoto-smart-stream.local",
                hashed_password=hashed,
                is_active=True,
                is_admin=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print(f"Lambda: ✓ Default admin user created (id: {admin_user.id})")
            logger.info("✓ Default admin user created in Lambda")
        else:
            print(f"Lambda: Admin user already exists (id: {admin_user.id})")
            logger.info(f"Admin user already exists (id: {admin_user.id})")
    except Exception as e:
        print(f"Lambda: ERROR creating default admin user: {e}")
        logger.error(f"Error creating default admin user: {e}")
        import traceback
        print(traceback.format_exc())
        db.rollback()
    finally:
        db.close()
    
    # Create FastAPI app
    app = create_app()
    
    # Wrap with Mangum for Lambda
    # lifespan="off" disables startup/shutdown events which don't work well in Lambda
    handler = Mangum(app, lifespan="off")
    
except ImportError as import_error:
    # Fallback handler for deployment testing
    error_msg = str(import_error)
    def handler(event, context):
        return {
            "statusCode": 500,
            "body": f"Error importing application: {error_msg}. Make sure yoto_smart_stream package is included in the Lambda package."
        }
except Exception as general_error:
    # Catch any other errors during import
    error_msg = str(general_error)
    def handler(event, context):
        return {
            "statusCode": 500,
            "body": f"Error initializing application: {error_msg}"
        }
