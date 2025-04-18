from fastapi import FastAPI
from milvus.search_candidates import search_candidates
from milvus.connect import connect_to_milvus
from job_operations import fetch_job_vector, get_applicants_for_job
app = FastAPI()

@app.get("/match/job/{job_id}/top-candidates")
def match_candidates(job_id: int, top_k: int = 5):
    connect_to_milvus()

    job_vector = fetch_job_vector(job_id)  # Your custom method
    candidate_ids = get_applicants_for_job(job_id)  # Query from your relational DB

    results = search_candidates(job_vector, candidate_ids, top_k)
    
    formatted = []
    for hits in results:
        for hit in hits:
            formatted.append({
                "candidate_id": hit.entity.get("candidate_id"),
                "name": hit.entity.get("name"),
                "skills": hit.entity.get("skills"),
                "experience_years": hit.entity.get("experience_years"),
                "score": hit.distance
            })

    return {"job_id": job_id, "top_matches": formatted}
