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
    
    # Initialize database on cold start
    logger = logging.getLogger(__name__)
    logger.info("Initializing database for Lambda...")
    init_db()
    
    # Create default admin user if doesn't exist  
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
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
            logger.info("✓ Default admin user created in Lambda")
    except Exception as e:
        logger.error(f"Error creating default admin user: {e}")
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
