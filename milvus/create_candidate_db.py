from pymilvus import Collection, CollectionSchema, FieldSchema, DataType
from connect import connect_to_milvus

def create_candidate_collection():
    connect_to_milvus()
    
    fields = [
        FieldSchema(name="candidate_id", dtype=DataType.INT64, is_primary=True, auto_id=False),
        FieldSchema(name="candidate_vector", dtype=DataType.FLOAT_VECTOR, dim=768),
        FieldSchema(name="name", dtype=DataType.VARCHAR, max_length=100),
    ]
    
    schema = CollectionSchema(fields=fields, description="Candidate resume embeddings")
    collection = Collection(name="candidates", schema=schema)
    
    # Create an IVF_FLAT index for the vector field
    index_params = {
        "metric_type": "COSINE",
        "index_type": "IVF_FLAT",
        "params": {"nlist": 1024}
    }
    collection.create_index(field_name="candidate_vector", index_params=index_params)
    print("Created and indexed candidates collection")
    return collection

if __name__ == "__main__":
    create_candidate_collection()
