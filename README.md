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

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd similarity
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the root directory with your Zilliz Cloud credentials:
```
ZILLIZ_URI=your_cluster_uri
ZILLIZ_TOKEN=your_cluster_token
```

5. Initialize the database:
```bash
python milvus/create_candidate_db.py
python milvus/create_job_db.py
```

## Project Structure

```
.
├── app/
│   ├── similarity_service.py    # Main FastAPI service
│   └── job_operations.py       # Job-related operations
├── milvus/
│   ├── connect.py              # Database connection handling
│   ├── create_candidate_db.py  # Candidate collection setup
│   ├── create_job_db.py       # Job collection setup
│   ├── insert_candidate.py    # Candidate insertion
│   ├── insert_job.py         # Job insertion
│   └── search_candidates.py   # Candidate search operations
├── test/
│   ├── test_connection.py     # Connection tests
│   └── test_job_operations.py # Job operations tests
├── .env                       # Environment variables
├── requirements.txt           # Python dependencies
└── README.md                 # This file
```

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