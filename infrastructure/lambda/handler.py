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
    
    # Create FastAPI app
    app = create_app()
    
    # Wrap with Mangum for Lambda
    # lifespan="off" disables startup/shutdown events which don't work well in Lambda
    handler = Mangum(app, lifespan="off")
    
except ImportError as e:
    # Fallback handler for deployment testing
    def handler(event, context):
        return {
            "statusCode": 500,
            "body": f"Error importing application: {str(e)}. Make sure yoto_smart_stream package is included in the Lambda package."
        }
