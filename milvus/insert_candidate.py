from pymilvus import Collection
from milvus.connect import connect_to_milvus

def insert_candidate(candidate_data):
    connect_to_milvus()
    collection = Collection("candidates")

    collection.insert(candidate_data)
    collection.load()
