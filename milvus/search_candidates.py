from pymilvus import Collection
from milvus.connect import connect_to_milvus

def search_candidates(job_vector, candidate_ids, top_k=5):
    connect_to_milvus()
    collection = Collection("candidates")
    collection.load()

    expr = f"candidate_id in {tuple(candidate_ids)}"
    
    results = collection.search(
        data=[job_vector],
        anns_field="candidate_vector",
        param={"metric_type": "COSINE", "params": {"nprobe": 10}},
        limit=top_k,
        expr=expr,
        output_fields=["candidate_id", "name"]
    )
    return results
