# SwiftSelect Similarity Service

A microservice for job-candidate matching using vector similarity search powered by Zilliz Cloud (Milvus).

## Features

- Vector similarity search for job-candidate matching
- FastAPI-based REST API
- Milvus/Zilliz Cloud integration for efficient vector search
- Scalable architecture for handling large numbers of jobs and candidates

## Prerequisites

- Python 3.8+
- Zilliz Cloud account and credentials
- pip (Python package manager)



## Usage

1. Start the service:
```bash
uvicorn app.similarity_service:app --reload
```

2. Access the API documentation:
- OpenAPI documentation: http://localhost:8000/docs
- ReDoc documentation: http://localhost:8000/redoc

## API Endpoints

- `GET /match/job/{job_id}/top-candidates`
  - Get top matching candidates for a specific job
  - Query parameters:
    - `top_k`: Number of candidates to return (default: 5)

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
