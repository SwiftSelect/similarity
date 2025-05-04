# SwiftSelect Similarity Service

A microservice for job-candidate matching and job recommendations using vector similarity search powered by Milvus/Zilliz Cloud and Redis.

## Features

- Vector embeddings generation for job postings and candidate resumes
- Kafka-based messaging system for processing jobs and candidates
- Redis Cloud integration for efficient storage and retrieval of similarity scores
- Milvus/Zilliz Cloud integration for vector storage and search
- Unified FastAPI service for accessing all endpoints
- Scalable architecture for handling large numbers of jobs and candidates
- Single command to start the entire service stack

## Architecture

The system consists of the following components:

1. **Embeddings API**: Generates vector embeddings from text using pretrained or finetuned models
2. **Candidate Matching**: Processes job applications and matches candidates to specific jobs
3. **Job Recommendations**: Generates personalized job recommendations for candidates
4. **Redis Cloud**: Stores similarity scores and provides fast access to ranked candidates and job recommendations
5. **Milvus/Zilliz**: Stores vector embeddings for jobs and candidates
6. **Unified API**: Exposes endpoints for retrieving candidate matches and job recommendations

## Workflow

### Candidate Matching

1. **Job Posting**: When a job is posted, the system:
   - Extracts relevant text from the job description
   - Generates vector embeddings
   - Stores them in Milvus/Zilliz

2. **Candidate Application**: When a candidate applies, the system:
   - Extracts relevant text from the resume
   - Generates vector embeddings
   - Stores them in Milvus/Zilliz
   - Calculates similarity with the job
   - Stores similarity score in Redis Cloud

3. **Matching**: To find the best candidates for a job:
   - Query Redis Cloud sorted sets for pre-calculated similarity scores
   - Return candidates ordered by highest similarity

### Job Recommendations

1. **Candidate Profile Processing**: When a candidate profile is updated:
   - Extracts relevant text from candidate data
   - Generates vector embeddings
   - Stores them in Milvus/Zilliz
   - Finds similar jobs using vector similarity search
   - Stores top matching jobs in Redis Cloud

2. **Job Recommendations**: To provide personalized job recommendations:
   - Query Redis Cloud sorted sets for pre-calculated job matches
   - Return jobs ordered by highest similarity

## Prerequisites

- Python 3.8+
- Zilliz Cloud account and credentials
- Redis Cloud account and credentials (or local Redis server)
- Kafka server with Confluent Cloud support
- pip (Python package manager)

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables in a `.env` file:
```
# Zilliz/Milvus Configuration
ZILLIZ_URI=your_zilliz_uri
ZILLIZ_TOKEN=your_zilliz_token

# Redis Configuration
REDIS_HOST=your_redis_cloud_host
REDIS_PORT=your_redis_cloud_port
REDIS_PASSWORD=your_redis_cloud_password
REDIS_DB=0

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=your_kafka_bootstrap_servers
KAFKA_SASL_USERNAME=your_kafka_username
KAFKA_SASL_PASSWORD=your_kafka_password
```

## Usage

### Option 1: Start All Services with One Command (Recommended)

Use the master script to start all services together with proper dependency management:

```bash
python master.py
```

This will:
1. Start the Embeddings API
2. API for candidate-job matching and job recommendations
3. Start all three Kafka consumers in the correct order
4. Monitor all services and handle graceful shutdown with Ctrl+C

The master script manages dependencies and ensures all services start in the correct order. It also provides centralized logging from all services in a single console.

### Option 2: Start Services Individually

If you need more control, you can still start each service individually:

1. Start the Embeddings API service first:
```bash
python -m embeddings.embeddings-api
```

2. Start the specialized consumers to process Kafka messages:
```bash
# For job processing
python -m candidate_matching.job_consumer

# For candidate-job matching (applications)
python -m candidate_matching.candidate_consumer

# For job recommendations
python -m jobs_recommendation.consumer
```

3. Start the unified API service:
```bash
python main.py
```

4. Access the API documentation:
- Unified API: http://localhost:8000/docs

## API Endpoints

### Unified API (main.py)

- `GET /candidate-matching/matches/job/{job_id}`
  - Get top matching candidates for a specific job
  - Query parameters:
    - `limit`: Number of candidates to return (default: 10)
    - `include_details`: Whether to include additional candidate details (default: false)

- `GET /job-recommendations/recommendations/{candidate_id}`
  - Get recommended jobs for a specific candidate
  - Query parameters:
    - `limit`: Number of jobs to return (default: 10)
    - `include_details`: Whether to include additional job details (default: false)

## Project Structure

```
.
├── candidate_matching/        # Candidate-job application matching
│   ├── api.py                # API for candidate matching (deprecated)
│   ├── job_consumer.py       # Kafka consumer for job postings
│   ├── candidate_consumer.py # Kafka consumer for job applications
│   └── generic_consumers.py  # Combined consumer (deprecated)
├── jobs_recommendation/       # Personalized job recommendations
│   ├── api.py                # API for job recommendations (deprecated)
│   └── consumer.py           # Kafka consumer for candidate profiles
├── embeddings/               # Embedding generation services
│   └── embeddings-api.py     # API for generating embeddings
├── milvus/                   # Milvus/Zilliz connection and collection setup
├── main.py                   # Unified API service
├── master.py                 # Service orchestration script for starting all components
└── test/                     # Test suite
```

## Recent Updates

- **Service Orchestration**: Added `master.py` script to start and monitor all services with a single command
- **Split Kafka Consumers**: Separated the generic consumer into dedicated `job_consumer.py` and `candidate_consumer.py` for better separation of concerns
- **Unified API**: Combined the separate APIs into a single `main.py` service that exposes all endpoints under different prefixes
- **Redis Cloud Integration**: Migrated from local Redis to Redis Cloud for better scalability and reliability
- **Kafka Configuration**: Added support for Confluent Cloud Kafka connectivity with SASL authentication

## Testing

Run the tests:
```bash
python -m pytest test/
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request
