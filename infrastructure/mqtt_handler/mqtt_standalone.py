"""
Standalone MQTT Handler for ECS Fargate
Maintains persistent MQTT connection and handles token refresh
"""
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone, timedelta

import boto3
from yoto_api import YotoManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MQTTHandler:
    """Handles MQTT connection and token management"""
    
    def __init__(self):
        self.environment = os.environ.get('ENVIRONMENT', 'dev')
        self.client_id = os.environ.get('YOTO_CLIENT_ID')
        self.dynamodb_table = os.environ.get('DYNAMODB_TABLE')
        self.aws_region = os.environ.get('AWS_REGION', 'us-east-1')
        
        if not self.client_id:
            raise ValueError("YOTO_CLIENT_ID environment variable is required")
        if not self.dynamodb_table:
            raise ValueError("DYNAMODB_TABLE environment variable is required")
        
        # Initialize DynamoDB
        self.dynamodb = boto3.resource('dynamodb', region_name=self.aws_region)
        self.table = self.dynamodb.Table(self.dynamodb_table)
        
        # Initialize Yoto Manager
        self.yoto_manager = None
        
    def get_tokens_from_db(self):
        """Get Yoto tokens from DynamoDB"""
        try:
            response = self.table.get_item(
                Key={'PK': 'USER#admin', 'SK': 'PROFILE'}
            )
            item = response.get('Item', {})
            
            refresh_token = item.get('yoto_refresh_token')
            access_token = item.get('yoto_access_token')
            expires_at = item.get('yoto_token_expires_at')
            
            logger.info(f"Retrieved tokens from DynamoDB: refresh_token={'present' if refresh_token else 'missing'}")
            return refresh_token, access_token, expires_at
            
        except Exception as e:
            logger.error(f"Error retrieving tokens from DynamoDB: {e}")
            return None, None, None
    
    def save_tokens_to_db(self, refresh_token, access_token, expires_at):
        """Save Yoto tokens to DynamoDB"""
        try:
            # Convert datetime to ISO string if needed
            if isinstance(expires_at, datetime):
                expires_at = expires_at.isoformat()
            
            self.table.update_item(
                Key={'PK': 'USER#admin', 'SK': 'PROFILE'},
                UpdateExpression='SET yoto_refresh_token = :rt, yoto_access_token = :at, yoto_token_expires_at = :exp',
                ExpressionAttributeValues={
                    ':rt': refresh_token,
                    ':at': access_token,
                    ':exp': expires_at,
                }
            )
            logger.info("Saved tokens to DynamoDB")
            
        except Exception as e:
            logger.error(f"Error saving tokens to DynamoDB: {e}")
    
    async def initialize_yoto_manager(self):
        """Initialize Yoto Manager with tokens from DynamoDB"""
        refresh_token, access_token, expires_at = self.get_tokens_from_db()
        
        if not refresh_token:
            logger.error("No refresh token found in DynamoDB. Please authenticate first.")
            raise ValueError("No refresh token available")
        
        # Create Yoto Manager
        self.yoto_manager = YotoManager(client_id=self.client_id)
        self.yoto_manager.set_refresh_token(refresh_token)
        
        if access_token and expires_at:
            # Set existing tokens
            self.yoto_manager.access_token = access_token
            
            # Parse expiry time
            if isinstance(expires_at, str):
                try:
                    expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                except:
                    expires_at = None
            
            if expires_at:
                self.yoto_manager.token_expiry = expires_at
        
        # Refresh tokens if needed
        logger.info("Checking and refreshing tokens...")
        await asyncio.to_thread(self.yoto_manager.check_and_refresh_token)
        
        # Save refreshed tokens
        self.save_tokens_to_db(
            self.yoto_manager.refresh_token,
            self.yoto_manager.access_token,
            self.yoto_manager.token_expiry
        )
        
        logger.info("Yoto Manager initialized successfully")
    
    async def start_mqtt(self):
        """Start MQTT connection"""
        logger.info("Starting MQTT connection...")
        
        try:
            await asyncio.to_thread(self.yoto_manager.connect_to_mqtt)
            logger.info("MQTT connection established")
        except Exception as e:
            logger.error(f"Error starting MQTT: {e}")
            raise
    
    async def token_refresh_loop(self):
        """Periodically refresh tokens (every 12 hours)"""
        while True:
            try:
                await asyncio.sleep(12 * 3600)  # 12 hours
                
                logger.info("Refreshing tokens...")
                await asyncio.to_thread(self.yoto_manager.check_and_refresh_token)
                
                self.save_tokens_to_db(
                    self.yoto_manager.refresh_token,
                    self.yoto_manager.access_token,
                    self.yoto_manager.token_expiry
                )
                
                logger.info("Tokens refreshed successfully")
                
            except Exception as e:
                logger.error(f"Error in token refresh loop: {e}")
                # Continue running even if refresh fails
    
    async def mqtt_loop(self):
        """Keep MQTT connection alive"""
        try:
            await asyncio.to_thread(self.yoto_manager.mqtt_client.loop_forever)
        except Exception as e:
            logger.error(f"MQTT loop error: {e}")
            raise
    
    async def run(self):
        """Main run loop"""
        logger.info(f"Starting MQTT Handler for environment: {self.environment}")
        
        # Initialize
        await self.initialize_yoto_manager()
        
        # Start MQTT
        await self.start_mqtt()
        
        # Run both loops concurrently
        await asyncio.gather(
            self.mqtt_loop(),
            self.token_refresh_loop(),
        )


async def main():
    """Main entry point"""
    handler = MQTTHandler()
    
    try:
        await handler.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
