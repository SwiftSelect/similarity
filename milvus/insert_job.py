from pymilvus import Collection
from milvus.connect import connect_to_milvus

def insert_job(job_data):
    connect_to_milvus()
    collection = Collection("jobs")

    collection.insert(job_data)
    collection.load()
