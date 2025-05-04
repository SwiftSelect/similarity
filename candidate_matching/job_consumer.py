from confluent_kafka import Consumer, Producer
import json
import httpx
import asyncio
import logging
import traceback
import os
import sys
import datetime
import numpy as np
import redis
from dotenv import load_dotenv
from pymilvus import MilvusClient

load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv('bootstrap.servers')
KAFKA_USERNAME = os.getenv('sasl.username')
KAFKA_PASSWORD = os.getenv('sasl.password')
CLIENT_ID1 = os.getenv('client.id1')
print(KAFKA_BOOTSTRAP_SERVERS)
print(KAFKA_USERNAME)
print(KAFKA_PASSWORD)
print(CLIENT_ID1)

client = MilvusClient(
    uri=os.getenv("ZILLIZ_URI"),
    token=os.getenv("ZILLIZ_TOKEN")
)

# Redis configuration
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST'),
    port=int(os.getenv('REDIS_PORT')),
    db=int(os.getenv('REDIS_DB')),
    password=os.getenv('REDIS_PASSWORD'),
    decode_responses=True
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Kafka consumer configuration
consumer_conf = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'security.protocol': 'SASL_SSL',
    'sasl.mechanisms': 'PLAIN',
    'sasl.username': KAFKA_USERNAME,
    'sasl.password': KAFKA_PASSWORD,
    'client.id': CLIENT_ID1,
    'group.id': 'job_matching_group',
    'auto.offset.reset': 'earliest'
}
consumer = Consumer(consumer_conf)
consumer.subscribe(['jobs_topic'])

# Embeddings API URL
EMBEDDINGS_API_URL = 'http://localhost:8003/embedding'

def init_redis():
    """Check Redis connection and clear any previous data if needed"""
    try:
        # Test the connection
        redis_client.ping()
        logger.info("Successfully connected to Redis")
        return True
    except redis.ConnectionError as e:
        logger.error(f"Could not connect to Redis: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error initializing Redis: {str(e)}")
        return False

async def extract_job_text(job_data):
    """Extract relevant text from job data for embedding"""
    text_parts = []
    
    # Add job title
    if job_data.get('title'):
        text_parts.append(job_data['title'])

    # Add job description
    if job_data.get('description'):
        text_parts.append(job_data['description'])
    
    # Add job requirements
    if job_data.get('overview'):
        text_parts.append(job_data['overview'])
    
    # Add skills required
    if job_data.get('skills'):
        if isinstance(job_data['skills'], list):
            text_parts.append(' '.join(job_data['skills']))
        elif isinstance(job_data['skills'], str):
            text_parts.append(job_data['skills'])
    
    if job_data.get('experience'):
        text_parts.append(job_data['experience'])
    
    return ' '.join(text_parts).strip()

async def generate_embedding(text, identifier):
    """Generate embedding for the given text"""
    payload = {
        'text': text,
        'model_type': 'pretrained'
    }
    logger.info(f"Sending payload to API for {identifier}: {payload}")

    async with httpx.AsyncClient(timeout=30.0) as http_client:
        response = await http_client.post(EMBEDDINGS_API_URL, json=payload)
        logger.info(f"API response status for {identifier}: {response.status_code}")
        response.raise_for_status()
        embeddings_data = response.json()
    
    return embeddings_data['embedding']

async def process_job_message(data):
    """Process a job message"""
    job_id = data.get('jobId')
    if not job_id:
            logger.error(f"Missing job ID in data: {data}")
            return False

    logger.info(f"Processing job: {job_id}")

    
    # Extract text for embedding
    text_to_embed = await extract_job_text(data)
    
    # Fallback to JSON if no text found
    if not text_to_embed:
        logger.warning(f"No relevant text found for job {job_id}, using JSON fallback")
        text_to_embed = json.dumps(data)
    
    if not text_to_embed.strip():
        logger.error(f"Empty text for job {job_id}, skipping")
        return
    
    # Generate embedding
    embedding = await generate_embedding(text_to_embed, f"job:{job_id}")
    
    # Prepare data for Milvus
    data_to_insert = {
        'job_id': job_id,
        'job_vector': embedding
    }
    
    # Insert into jobs collection
    res = client.insert(
        collection_name="jobs",
        data=data_to_insert
    )
    logger.info(f"Job data inserted into Milvus: {res}")
    
    return embedding

async def process_message(message):
    try:
        # Parse the Kafka message
        data = json.loads(message.value().decode('utf-8'))
        logger.info(f"Received job message: {json.dumps(data, indent=2)[:200]}...")  # Truncate for brevity
        await process_job_message(data)
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Embeddings API error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}\n{traceback.format_exc()}")

async def main():
    logger.info("Starting job Kafka consumer for embeddings...")
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            logger.error(f"Consumer error: {msg.error()}")
            continue
        await process_message(msg)

if __name__ == "__main__":
    # Initialize Redis
    if init_redis():
        asyncio.run(main())
    else:
        logger.error("Failed to initialize Redis. Exiting.")
        sys.exit(1) 