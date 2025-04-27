# SwiftSelect Similarity Service

A microservice for job-candidate matching and job recommendations using vector similarity search powered by Milvus/Zilliz Cloud and Redis.

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
2. **Candidate Matching**: Processes job applications and matches candidates to specific jobs
3. **Job Recommendations**: Generates personalized job recommendations for candidates
4. **Redis**: Stores similarity scores and provides fast access to ranked candidates and job recommendations
5. **Milvus/Zilliz**: Stores vector embeddings for jobs and candidates
6. **APIs**: Expose endpoints for retrieving candidate matches and job recommendations

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
   - Stores similarity score in Redis

3. **Matching**: To find the best candidates for a job:
   - Query Redis sorted sets for pre-calculated similarity scores
   - Return candidates ordered by highest similarity

### Job Recommendations

1. **Candidate Profile Processing**: When a candidate profile is updated:
   - Extracts relevant text from candidate data
   - Generates vector embeddings
   - Stores them in Milvus/Zilliz
   - Finds similar jobs using vector similarity search
   - Stores top matching jobs in Redis

2. **Job Recommendations**: To provide personalized job recommendations:
   - Query Redis sorted sets for pre-calculated job matches
   - Return jobs ordered by highest similarity

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

1. Start the Embeddings API service first:
```bash
python -m embeddings.embeddings-api
```

2. Start the consumers to process Kafka messages:
```bash
# For candidate-job matching (applications)
python -m candidate_matching.generic_consumers

# For job recommendations
python -m jobs_recommendation.consumer
```

3. Start the API services:
```bash
# Candidate matching API
python -m candidate_matching.api

# Job recommendations API
python -m jobs_recommendation.api
```

4. Access the API documentation:
- Candidate Matching API: http://localhost:8000/docs
- Job Recommendations API: http://localhost:8002/docs

## API Endpoints

### Candidate Matching API

- `GET /matches/job/{job_id}`
  - Get top matching candidates for a specific job
  - Query parameters:
    - `limit`: Number of candidates to return (default: 10)
    - `include_details`: Whether to include additional candidate details (default: false)

### Job Recommendations API

- `GET /recommendations/{candidate_id}`
  - Get recommended jobs for a specific candidate
  - Query parameters:
    - `limit`: Number of jobs to return (default: 10)
    - `include_details`: Whether to include additional job details (default: false)

## Project Structure

```
.
├── candidate_matching/       # Candidate-job application matching
│   ├── api.py               # API for candidate matching
│   └── generic_consumers.py # Kafka consumers for job applications
├── jobs_recommendation/      # Personalized job recommendations
│   ├── api.py               # API for job recommendations
│   └── consumer.py          # Kafka consumer for candidate profiles
├── embeddings/              # Embedding generation services
├── milvus/                  # Milvus/Zilliz connection and collection setup
└── test/                    # Test suite
```

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
