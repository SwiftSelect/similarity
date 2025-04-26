# SwiftSelect Similarity Service

A microservice for job-candidate matching using vector similarity search powered by Milvus/Zilliz Cloud and Redis.

## Features

- Vector embeddings generation for job postings and candidate resumes
- Kafka-based messaging system for processing jobs and candidates
- Redis sorted sets for efficient storage and retrieval of similarity scores
- Milvus/Zilliz Cloud integration for vector storage and search
- FastAPI-based REST API for retrieving top candidates
- Scalable architecture for handling large numbers of jobs and candidates

## Architecture

The system consists of the following components:

1. **Embeddings API**: Generates vector embeddings from text using pretrained or finetuned models
2. **Generic Consumer**: Processes messages from Kafka, generates embeddings, and stores them
3. **Redis**: Stores similarity scores and provides fast access to ranked candidates
4. **Milvus/Zilliz**: Stores vector embeddings for jobs and candidates
5. **Matching API**: Exposes endpoints for retrieving top candidate matches

## Workflow

1. **Job Posting**: When a job is posted, the system:
   - Extracts relevant text from the job description
   - Generates vector embeddings
   - Stores them in Milvus/Zilliz

2. **Candidate Application**: When a candidate applies, the system:
   - Extracts relevant text from the resume
   - Generates vector embeddings
   - Stores them in Milvus/Zilliz
   - Calculates similarity with the job
   - Stores similarity score in Redis

3. **Matching**: To find the best candidates for a job:
   - Query Redis sorted sets for pre-calculated similarity scores
   - Return candidates ordered by highest similarity

## Prerequisites

- Python 3.8+
- Zilliz Cloud account and credentials
- Redis server
- Kafka server
- pip (Python package manager)

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables in a `.env` file:
```
ZILLIZ_URI=your_zilliz_uri
ZILLIZ_TOKEN=your_zilliz_token
REDIS_HOST=localhost
REDIS_PORT=6379
```

## Usage

1. Start the consumer to process Kafka messages:
```bash
python -m app.generic_consumers
```

2. Start the API service:
```bash
python -m app.api
```

3. Access the API documentation:
- OpenAPI documentation: http://localhost:8000/docs
- ReDoc documentation: http://localhost:8000/redoc

## API Endpoints

- `GET /matches/job/{job_id}`
  - Get top matching candidates for a specific job
  - Query parameters:
    - `limit`: Number of candidates to return (default: 10)
    - `include_details`: Whether to include additional candidate details (default: false)

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
