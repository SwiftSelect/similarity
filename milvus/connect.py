from pymilvus import connections
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def connect_to_milvus():
    # Load environment variables from .env file
    load_dotenv()
    
    # Get credentials from environment variables
    uri = os.getenv("ZILLIZ_URI")
    token = os.getenv("ZILLIZ_TOKEN")
    
    if not uri or not token:
        raise ValueError("ZILLIZ_URI and ZILLIZ_TOKEN environment variables must be set")
    
    logger.debug(f"Attempting to connect to Zilliz Cloud at: {uri}")
    try:
        connections.connect(
            alias="default",
            uri=uri,
            token=token
        )
        logger.debug("Connection established successfully")
    except Exception as e:
        logger.error(f"Failed to connect: {str(e)}")
        raise
