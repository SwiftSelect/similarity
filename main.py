import os
import sys
import json
import redis
from fastapi import FastAPI, HTTPException, Query, APIRouter
from dotenv import load_dotenv
from typing import List, Dict, Optional
from pymilvus import MilvusClient

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(
    title="SwiftSelect API",
    description="Combined API for candidate-job matching and job recommendations",
    version="1.0.0"
)

# Redis configuration
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST'),
    port=int(os.getenv('REDIS_PORT')),
    db=int(os.getenv('REDIS_DB')),
    password=os.getenv('REDIS_PASSWORD'),
    decode_responses=True,  # Automatically decode responses to strings
)

# Milvus client for retrieving additional details
milvus_client = MilvusClient(
    uri=os.getenv("ZILLIZ_URI"),
    token=os.getenv("ZILLIZ_TOKEN")
)

# Create routers for each API to organize the endpoints
candidate_router = APIRouter(prefix="/candidate-matching", tags=["Candidate Matching"])
jobs_router = APIRouter(prefix="/job-recommendations", tags=["Job Recommendations"])

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "SwiftSelect API is running",
        "endpoints": {
            "candidate_matching": "/candidate-matching/",
            "job_recommendations": "/job-recommendations/"
        }
    }

# --- Candidate Matching Endpoints ---
@candidate_router.get("/")
async def candidate_matching_root():
    return {"message": "Candidate-Job Matching API is running"}

@candidate_router.get("/matches/job/{job_id}")
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

# --- Job Recommendations Endpoints ---
@jobs_router.get("/")
async def job_recommendations_root():
    return {"message": "Job Recommendations API is running"}

@jobs_router.get("/recommendations/{candidate_id}")
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

# Register routers
app.include_router(candidate_router)
app.include_router(jobs_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004) 