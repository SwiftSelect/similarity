from pymilvus import Collection, CollectionSchema, FieldSchema, DataType
from connect import connect_to_milvus

def create_job_collection():
    connect_to_milvus()

    fields = [
        FieldSchema(name="job_id", dtype=DataType.INT64, is_primary=True, auto_id=False),
        FieldSchema(name="job_vector", dtype=DataType.FLOAT_VECTOR, dim=768),
    ]
    
    schema = CollectionSchema(fields=fields, description="Job description embeddings")
    collection = Collection(name="jobs", schema=schema)
    
    # Create an IVF_FLAT index for the vector field
    index_params = {
        "metric_type": "COSINE",
        "index_type": "IVF_FLAT",
        "params": {"nlist": 1024}
    }
    collection.create_index(field_name="job_vector", index_params=index_params)
    print("Created and indexed jobs collection")
    return collection

if __name__ == "__main__":
    create_job_collection()
