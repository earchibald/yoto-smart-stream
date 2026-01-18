"""
AWS Lambda handler for Yoto Smart Stream API
Uses Mangum to adapt FastAPI for Lambda
Force update: 2026-01-18T00:00:00Z
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
    import logging
    
    # Configure logging first
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Initialize database on cold start
    print("Lambda: Initializing database...")  # Print to ensure output
    logger.info("Initializing database for Lambda...")
    init_db()
    print("Lambda: Database initialized")
    logger.info("Lambda: Database initialized successfully")
    
    # Create FastAPI app (admin user bootstrap happens in app lifespan)
    app = create_app()
    
    # Wrap with Mangum for Lambda
    # lifespan="auto" enables startup/shutdown events for proper initialization
    handler = Mangum(app, lifespan="auto")
    
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
    import traceback
    error_msg = str(general_error)
    error_trace = traceback.format_exc()
    print(f"Lambda ERROR during initialization: {error_msg}")
    print(error_trace)
    def handler(event, context):
        return {
            "statusCode": 500,
            "body": f"Error initializing application: {error_msg}"
        }
