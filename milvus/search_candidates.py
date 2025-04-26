import logging
from pymilvus import Collection
from milvus.connect import connect_to_milvus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def search_candidates(job_vector, candidate_ids, top_k=5):
    """
    Search for candidates based on job vector similarity.
    
    Args:
        job_vector (list): 768-dimensional vector representing the job
        candidate_ids (list): List of candidate IDs to search among
        top_k (int): Number of top candidates to return (default: 5)
        
    Returns:
        list: List of dictionaries containing candidate details and similarity scores
        
    Raises:
        ValueError: If job_vector is not 768-dimensional
        Exception: If database operations fail
    """
    try:
        # Validate input vector
        if len(job_vector) != 1024:
            raise ValueError("Job vector must be 1024-dimensional")
            
        # Connect to Milvus
        connect_to_milvus()
        collection = Collection("candidates")
        collection.load()
        
        # Handle empty candidate_ids list
        if not candidate_ids:
            logger.warning("No candidate IDs provided, searching all candidates")
            expr = None
        else:
            # Create filter expression for string IDs
            id_list = [f"'{id}'" for id in candidate_ids]
            expr = f"candidate_id in [{','.join(id_list)}]"
        
        # Search parameters
        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 10}
        }
        
        # Perform search
        results = collection.search(
            data=[job_vector],
            anns_field="candidate_vector",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["candidate_id", "name"]
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Error searching candidates: {str(e)}")
        raise
