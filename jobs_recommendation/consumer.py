from confluent_kafka import Consumer
import json
import httpx
import asyncio
import logging
import traceback
import os
import datetime
import numpy as np
import redis
from dotenv import load_dotenv
from pymilvus import MilvusClient


load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv('bootstrap.servers')
KAFKA_USERNAME = os.getenv('sasl.username')
KAFKA_PASSWORD = os.getenv('sasl.password')
CLIENT_ID2 = os.getenv('client.id2')

# Milvus Client
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
    'client.id': CLIENT_ID2,
    'group.id': 'job_recommendation_group',
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': False
}
consumer = Consumer(consumer_conf)
consumer.subscribe(['candidate_data_topic'])

# Embeddings API URL
EMBEDDINGS_API_URL = 'http://localhost:8003/embedding'

# Number of top matching jobs to find
TOP_MATCHES_LIMIT = 10

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

def store_job_recommendations(candidate_id, job_recommendations):
    """Store job recommendations for a candidate in Redis"""
    try:
        # Store as a sorted set for ranking
        candidate_recommendations_key = f"recommendations:{candidate_id}:jobs"
        
        # Clear any existing recommendations
        redis_client.delete(candidate_recommendations_key)
        
        # Add all jobs with their scores
        if job_recommendations:
            job_scores = {job_id: score for job_id, score in job_recommendations}
            redis_client.zadd(candidate_recommendations_key, job_scores)
            
            # Set an expiration time (e.g., 7 days)
            redis_client.expire(candidate_recommendations_key, 7 * 24 * 60 * 60)
            
        logger.info(f"Stored {len(job_recommendations)} job recommendations for candidate {candidate_id}")
        return True
    except Exception as e:
        logger.error(f"Error storing job recommendations in Redis: {str(e)}")
        return False

async def extract_candidate_text(structured_data):
    """Extract relevant text from candidate data for embedding"""
    text_parts = []

    # Add experience responsibilities
    for exp in structured_data.get('experience', []) or []:
        if exp.get('title'):
            text_parts.append(exp['title'])
        text_parts.extend(exp.get('responsibilities', []) or [])

    # Add project descriptions
    for project in structured_data.get('projects', []) or []:
        if project.get('description'):
            text_parts.append(project['description'])
        # Add technologies if present
        technologies = project.get('technologies', []) or []
        if technologies:
            # Join technologies into a string
            text_parts.append(' '.join(technologies))

    # Add technical skills
    technical_skills = structured_data.get('technical_skills', {}) or {}
    for skill_category in ['languages', 'tools']:
        skills = technical_skills.get(skill_category, []) or []
        if skills:
            text_parts.append(' '.join(skills))

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

async def find_matching_jobs(candidate_vector, limit=10):
    """Find top matching jobs using vector similarity search in Milvus"""
    try:
        # Perform a vector similarity search in the jobs collection
        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 16}
        }
        
        results = client.search(
            collection_name="jobs",
            data=[candidate_vector],
            limit=limit,
            output_fields=["job_id"],
            search_params=search_params
        )
        
        if not results or len(results) == 0:
            logger.warning("No job matches found")
            return []
        
        # Extract job IDs and scores
        job_matches = []
        for result in results[0]:  # First element contains results for our single query vector
            job_id = result["entity"]["job_id"]
            similarity = result["distance"]  # This is the similarity score
            job_matches.append((job_id, similarity))
        
        logger.info(f"Found {len(job_matches)} matching jobs")
        return job_matches
    
    except Exception as e:
        logger.error(f"Error finding matching jobs: {str(e)}")
        return []

async def process_candidate_recommendation(data):
    """Process a candidate message to generate job recommendations"""
    candidate_id = data.get('candidateId')
    structured_data = data.get('structuredData')
    
    if candidate_id == 'unknown':
        logger.error("Missing candidateId, cannot process recommendation")
        return
    
    logger.info(f"Processing recommendation for candidate: {candidate_id}")
    
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
    
    # Store candidate embedding in Milvus
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
    
    # Find matching jobs for this candidate
    logger.info(f"Finding job recommendations for candidate {candidate_id}")
    job_matches = await find_matching_jobs(embedding, limit=TOP_MATCHES_LIMIT)
    
    if job_matches:
        # Store the recommendations in Redis
        success = store_job_recommendations(candidate_id, job_matches)
        if success:
            logger.info(f"Successfully stored {len(job_matches)} job recommendations for candidate {candidate_id}")
        else:
            logger.error(f"Failed to store job recommendations for candidate {candidate_id}")
    else:
        logger.warning(f"No job matches found for candidate {candidate_id}")
    
    return embedding, job_matches

async def process_message(message):
    try:
        # Parse the Kafka message
        data = json.loads(message.value().decode('utf-8'))
        topic = message.topic()
        
        logger.info(f"Received job recommendation message from topic {topic}: {json.dumps(data, indent=2)}")
        
        # Process for recommendations
        await process_candidate_recommendation(data)
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Embeddings API error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}\n{traceback.format_exc()}")

async def main():
    logger.info("Starting Job Recommendations Kafka consumer...")
    while True:
        msg = await asyncio.to_thread(consumer.poll, 1.0)
        if msg is None:
            continue
        if msg.error():
            logger.error(f"Consumer error: {msg.error()}")
            continue
        try :
            await process_message(msg)
            await asyncio.to_thread(consumer.commit, message=msg)
        except Exception as e:
            logger.error(f"Error committing message: {str(e)}\n{traceback.format_exc()}")

if __name__ == "__main__":
    try:
        # Test Redis connection
        redis_client.ping()
        logger.info("Successfully connected to Redis")
        
        # Start the consumer
        asyncio.run(main())
    except redis.ConnectionError as e:
        logger.error(f"Could not connect to Redis: {str(e)}")
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")