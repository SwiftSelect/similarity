"""
DEPRECATED: This API file is no longer the primary API endpoint.
It has been combined with the candidate_matching API into a single unified API.
Please use the main.py file at the root level of the project instead.
"""

from fastapi import FastAPI, HTTPException, Query
from typing import List, Dict, Optional
import os
import redis
from dotenv import load_dotenv
from pymilvus import MilvusClient

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(
    title="Job Recommendations API",
    description="API for retrieving job recommendations for candidates",
    version="1.0.0"
)

# Redis configuration
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=int(os.getenv('REDIS_DB', 0)),
    password=os.getenv('REDIS_PASSWORD', None),
    decode_responses=True
)

# Milvus client for retrieving job details
milvus_client = MilvusClient(
    uri=os.getenv("ZILLIZ_URI"),
    token=os.getenv("ZILLIZ_TOKEN")
)

@app.get("/")
async def root():
    return {"message": "Job Recommendations API is running"}

@app.get("/recommendations/{candidate_id}")
async def get_job_recommendations(
    candidate_id: str, 
    limit: int = Query(10, ge=1, le=100),
    include_details: bool = Query(False)
):
    """
    Get job recommendations for a candidate based on their profile.
    
    Parameters:
    - candidate_id: The ID of the candidate
    - limit: Maximum number of recommendations to return (default: 10, max: 100)
    - include_details: Whether to include additional job details (default: false)
    """
    try:
        # Get recommendations from Redis sorted set
        recommendations_key = f"recommendations:{candidate_id}:jobs"
        top_jobs = redis_client.zrevrange(
            recommendations_key, 0, limit-1, withscores=True
        )
        
        if not top_jobs:
            return {"candidate_id": candidate_id, "recommendations": []}
        
        # Format the results
        recommendations = []
        for job_id, score in top_jobs:
            recommendation = {
                "job_id": job_id,
                "similarity_score": score
            }
            
            # Get additional data if requested
            if include_details:
                try:
                    # Get job details from Milvus if available
                    job_results = milvus_client.get(
                        collection_name="jobs",
                        ids=[job_id],
                        output_fields=["job_id"]  # Add any other fields if stored
                    )
                    
                    if job_results and job_id in job_results:
                        # This could be expanded if you store more job metadata in Milvus
                        recommendation["details"] = job_results[job_id]
                except Exception as e:
                    pass  # Continue even if details retrieval fails
            
            recommendations.append(recommendation)
            
        return {
            "candidate_id": candidate_id,
            "total_recommendations": len(recommendations),
            "recommendations": recommendations
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving recommendations: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)