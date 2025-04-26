from confluent_kafka import Consumer, Producer
import json
import httpx
import asyncio
import logging
import traceback
import os
from dotenv import load_dotenv
from pymilvus import MilvusClient
# from pymilvus import Collection
# from milvus.connect import connect_to_milvus

load_dotenv()



client = MilvusClient(
    uri=os.getenv("ZILLIZ_URI"),
    token=os.getenv("ZILLIZ_TOKEN")
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Kafka consumer configuration
consumer_conf = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'embeddings_consumer_group',
    'auto.offset.reset': 'earliest'
}
consumer = Consumer(consumer_conf)
consumer.subscribe(['processed_resume_topic'])

# Kafka producer configuration
producer_conf = {
    'bootstrap.servers': 'localhost:9092'
}
producer = Producer(producer_conf)

# Embeddings API URL
EMBEDDINGS_API_URL = 'http://localhost:8001/embedding'

async def process_message(message):
    try:
        # Parse the Kafka message
        data = json.loads(message.value().decode('utf-8'))
        filename = data.get('filename')
        structured_data = data.get('structured_data')
        logger.info(f"Received message for {filename}: {json.dumps(data, indent=2)}")

        # Extract relevant text for embeddings
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

        # Combine text parts into a single string
        text_to_embed = ' '.join(text_parts).strip()
        if not text_to_embed:
            logger.warning(f"No relevant text found for {filename}, using JSON fallback")
            text_to_embed = json.dumps(structured_data)

        logger.info(f"Text to embed for {filename}: {text_to_embed[:500]}...")  # Truncate for brevity

        # Validate text
        if not text_to_embed.strip():
            logger.error(f"Empty text for {filename}, skipping")
            return

        # Call embeddings API
        payload = {
            'text': text_to_embed,
            'model_type': 'pretrained'
        }
        logger.info(f"Sending payload to API for {filename}: {payload}")

        async with httpx.AsyncClient(timeout=30.0) as http_client:
            response = await http_client.post(EMBEDDINGS_API_URL, json=payload)
            logger.info(f"API response status for {filename}: {response.status_code}, text: {response.text}")
            response.raise_for_status()
            embeddings_data = response.json()
            logger.info(f"API response data for {filename}: {embeddings_data}")

        # Prepare message with embeddings
        output_message = {
            'filename': filename,
            'candidate_id': data.get('candidateID', 'unknown'),
            'structured_data': structured_data,
            'embeddings': embeddings_data['embedding'],
            'model_type': embeddings_data['model_type']
        }
        
        data_to_insert = {
            'name': filename,
            'candidate_id': data.get('candidateID', 'unknown'),
            'candidate_vector': embeddings_data['embedding'],
            # 'model_type': embeddings_data['model_type']
        }
        
        res = client.insert(
            collection_name="candidates",
            data=data_to_insert
        )
        print("Data inserted into Milvus:", res)

        # Send embeddings to a new Kafka topic
        # output_topic = 'embedded_resume_topic'
        # producer.produce(output_topic, json.dumps(output_message).encode('utf-8'))
        # producer.flush()

        logger.info(f"Processed message for {filename}: Embeddings generated") #and sent to {output_topic}")

    except httpx.HTTPStatusError as e:
        logger.error(f"Embeddings API error for {filename}: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        logger.error(f"Error processing message for {filename}: {str(e)}\n{traceback.format_exc()}")

async def main():
    logger.info("Starting Kafka consumer for embeddings...")
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            logger.error(f"Consumer error: {msg.error()}")
            continue
        await process_message(msg)

if __name__ == "__main__":
    asyncio.run(main())