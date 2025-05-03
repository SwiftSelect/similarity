# app/api.py
import os
import sys
import json
import redis
from fastapi import FastAPI, HTTPException, Query
from dotenv import load_dotenv
from typing import List, Dict, Optional
from pymilvus import MilvusClient

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(
    title="Candidate-Job Matching API",
    description="API for retrieving candidate-job similarity matches",
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

# Milvus client for retrieving additional details if needed
milvus_client = MilvusClient(
    uri=os.getenv("ZILLIZ_URI"),
    token=os.getenv("ZILLIZ_TOKEN")
)

@app.get("/")
async def root():
    return {"message": "Candidate-Job Matching API is running"}

@app.get("/matches/job/{job_id}")
async def get_top_candidates(
    job_id: str, 
    limit: int = Query(10, ge=1, le=100),
    include_details: bool = Query(False)
):
    """
    Get top candidates for a specific job based on similarity scores.
    
    Parameters:
    - job_id: The ID of the job
    - limit: Maximum number of candidates to return (default: 10, max: 100)
    - include_details: Whether to include additional candidate details from Milvus
    """
    try:
        # Get top candidates from Redis sorted set
        job_candidates_key = f"job:{job_id}:candidates"
        top_candidates = redis_client.zrevrange(
            job_candidates_key, 0, limit-1, withscores=True
        )
        
        if not top_candidates:
            return {"job_id": job_id, "matches": []}
        
        # Format the results
        matches = []
        for candidate_id, score in top_candidates:
            match_data = {
                "candidate_id": candidate_id,
                "similarity_score": score
            }
            
            # Get additional data if requested
            if include_details:
                try:
                    # Get match details from Redis hash
                    match_key = f"match:{job_id}:{candidate_id}"
                    match_details = redis_client.hgetall(match_key)
                    if match_details:
                        match_data["details"] = match_details
                        # Use candidate_name from Redis if available
                        if "candidate_name" in match_details:
                            match_data["candidate_name"] = match_details["candidate_name"]
                        
                    # If candidate_name not in Redis, try to get it from Milvus as fallback
                    if "candidate_name" not in match_data:
                        candidate_res = milvus_client.get(
                            collection_name="candidates",
                            ids=[candidate_id],
                            output_fields=["name", "candidate_id"]
                        )
                        if candidate_res and candidate_id in candidate_res:
                            match_data["candidate_name"] = candidate_res[candidate_id].get("name", "Unknown")
                except Exception as e:
                    pass  # Continue even if details retrieval fails
            
            matches.append(match_data)
            
        return {
            "job_id": job_id,
            "total_matches": len(matches),
            "matches": matches
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving matches: {str(e)}")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)