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

client = MilvusClient(
    uri=os.getenv("ZILLIZ_URI"),
    token=os.getenv("ZILLIZ_TOKEN")
)

# Redis configuration
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=int(os.getenv('REDIS_DB', 0)),
    password=os.getenv('REDIS_PASSWORD', None),
    decode_responses=True  # Automatically decode responses to strings
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Kafka consumer configuration
consumer_conf = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'generic_embeddings_consumer_group',
    'auto.offset.reset': 'earliest'
}
consumer = Consumer(consumer_conf)
consumer.subscribe(['processed_resume_topic', 'jobs_topic'])

# Kafka producer configuration (if needed)
producer_conf = {
    'bootstrap.servers': 'localhost:9092'
}
producer = Producer(producer_conf)

# Embeddings API URL
EMBEDDINGS_API_URL = 'http://localhost:8001/embedding'

def init_redis():
    """Check Redis connection and clear any previous data if needed"""
    try:
        # Test the connection
        redis_client.ping()
        logger.info("Successfully connected to Redis")
        
        # Optionally, you can clear previous data:
        # redis_client.flushdb()
        # logger.info("Redis database flushed")
        
        return True
    except redis.ConnectionError as e:
        logger.error(f"Could not connect to Redis: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error initializing Redis: {str(e)}")
        return False

def calculate_similarity(vector1, vector2):
    """Calculate cosine similarity between two vectors"""
    vector1 = np.array(vector1)
    vector2 = np.array(vector2)
    
    # Calculate cosine similarity
    dot_product = np.dot(vector1, vector2)
    norm_a = np.linalg.norm(vector1)
    norm_b = np.linalg.norm(vector2)
    
    # Handle zero division
    if norm_a == 0 or norm_b == 0:
        return 0
    
    similarity = dot_product / (norm_a * norm_b)
    return float(similarity)

def store_similarity_score(job_id, candidate_id, application_id, similarity_score):
    """Store similarity score in Redis"""
    try:
        # Store detailed information as a hash
        match_key = f"match:{job_id}:{candidate_id}"
        redis_client.hset(match_key, mapping={
            'job_id': job_id,
            'candidate_id': candidate_id,
            'application_id': application_id,
            'similarity_score': similarity_score,
            'timestamp': datetime.datetime.now().isoformat()
        })
        
        # Add to a sorted set for this job (for ranking)
        # This allows retrieving candidates for a job sorted by score
        job_candidates_key = f"job:{job_id}:candidates"
        redis_client.zadd(job_candidates_key, {candidate_id: similarity_score})
        
        # Also add to a sorted set for this candidate (to find best matching jobs)
        candidate_jobs_key = f"candidate:{candidate_id}:jobs"
        redis_client.zadd(candidate_jobs_key, {job_id: similarity_score})
        
        logger.info(f"Stored similarity score {similarity_score} for job {job_id} and candidate {candidate_id}")
        return True
    except Exception as e:
        logger.error(f"Error storing similarity score in Redis: {str(e)}")
        return False

async def extract_candidate_text(structured_data):
    """Extract relevant text from candidate data for embedding"""
    text_parts = []

    # Add experience responsibilities
    for exp in structured_data.get('experience', []):
        text_parts.extend(exp.get('responsibilities', []))

    # Add project descriptions
    for project in structured_data.get('projects', []):
        if project.get('description'):
            text_parts.append(project['description'])

    # Add technical skills
    technical_skills = structured_data.get('technical_skills', {})
    for skill_category in ['programming_databases', 'frameworks', 'ml_genai', 'devops_tools']:
        skills = technical_skills.get(skill_category, [])
        if skills:
            text_parts.append(' '.join(skills))

    return ' '.join(text_parts).strip()

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

async def process_candidate_message(data):
    """Process a candidate message and calculate similarity with the job they're applying to"""
    candidate_id = data.get('candidateID', 'unknown')
    structured_data = data.get('structured_data', {})
    job_id = data.get('job_id')  # Job ID is always expected
    application_id = data.get('application_id', f"app_{candidate_id}_{job_id}")  # Generate an application ID if not provided
    
    if not job_id:
        logger.error(f"Missing job_id for candidate {candidate_id}, cannot process application")
        return
    
    # Extract text for embedding
    text_to_embed = await extract_candidate_text(structured_data)
    
    # Fallback to JSON if no text found
    if not text_to_embed:
        logger.warning(f"No relevant text found for candidate {candidate_id}, using JSON fallback")
        text_to_embed = json.dumps(structured_data)
    
    if not text_to_embed.strip():
        logger.error(f"Empty text for candidate {candidate_id}, skipping")
        return
    
    # Generate embedding
    embedding = await generate_embedding(text_to_embed, f"candidate:{candidate_id}")
    
    # Prepare data for Milvus
    data_to_insert = {
        'candidate_id': candidate_id,
        'candidate_vector': embedding
    }
    
    # Insert into candidates collection
    res = client.insert(
        collection_name="candidates",
        data=data_to_insert
    )
    logger.info(f"Candidate data inserted into Milvus: {res}")
    
    # Get job vector from Milvus - this is now the default flow
    logger.info(f"Calculating similarity for candidate {candidate_id} applying to job {job_id}")
    try:
        # Get job vector from Milvus
        job_results = client.get(
            collection_name="jobs",
            ids=[job_id],
            output_fields=["job_vector"]
        )
        
        if not job_results or not job_results.get(job_id):
            logger.error(f"Job vector not found for job_id: {job_id}")
            return embedding
        
        job_vector = job_results[job_id]["job_vector"]
        
        # Calculate similarity
        similarity_score = calculate_similarity(embedding, job_vector)
        logger.info(f"Similarity score between job {job_id} and candidate {candidate_id}: {similarity_score}")
        
        # Store similarity score in Redis
        success = store_similarity_score(job_id, candidate_id, application_id, similarity_score)
        
        if success:
            logger.info(f"Successfully stored similarity score for candidate {candidate_id} and job {job_id}")
        else:
            logger.error(f"Failed to store similarity score for candidate {candidate_id} and job {job_id}")
            
    except Exception as e:
        logger.error(f"Error calculating similarity: {str(e)}\n{traceback.format_exc()}")
    
    return embedding

async def process_job_message(data):
    """Process a job message"""
    job_id = data.get('job_id') or data.get('id')
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
        topic = message.topic()
        
        logger.info(f"Received message from topic {topic}: {json.dumps(data, indent=2)[:200]}...")  # Truncate for brevity
        
        # Determine message type and process accordingly
        if topic == 'processed_resume_topic' or 'candidateID' in data:
            # This is a candidate application message
            # (assumes all candidate messages include a job_id)
            await process_candidate_message(data)
        elif topic == 'jobs_topic' or ('job_id' in data and 'candidateID' not in data):
            # This is a job posting message
            await process_job_message(data)
        else:
            logger.warning(f"Unknown message type in topic {topic}: {json.dumps(data, indent=2)[:200]}...")
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Embeddings API error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}\n{traceback.format_exc()}")

async def main():
    logger.info("Starting generic Kafka consumer for embeddings...")
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            logger.error(f"Consumer error: {msg.error()}")
            continue
        await process_message(msg)

if __name__ == "__main__":
    # Initialize Redis instead of PostgreSQL
    if init_redis():
        asyncio.run(main())
    else:
        logger.error("Failed to initialize Redis. Exiting.")
        sys.exit(1)