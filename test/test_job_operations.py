from pymilvus import Collection
import numpy as np
from connect import connect_to_milvus
from job_operations import fetch_job_vector

def insert_test_job():
    """Insert a test job with known vector for testing"""
    connect_to_milvus()
    collection = Collection("jobs")
    collection.load()
    
    # Create a test vector (768 dimensions)
    test_vector = np.random.rand(768).tolist()
    test_job_id = 999999  # Using a high number to avoid conflicts
    
    # Insert test data
    entities = [{
        "job_id": test_job_id,
        "job_vector": test_vector
    }]
    
    try:
        collection.insert(entities)
        print(f"Test job {test_job_id} inserted successfully")
        return test_job_id, test_vector
    except Exception as e:
        print(f"Error inserting test job: {str(e)}")
        return None, None

def test_fetch_job_vector():
    """Test the fetch_job_vector function"""
    # Insert a test job
    test_job_id, expected_vector = insert_test_job()
    if not test_job_id:
        print("Failed to insert test job")
        return False
    
    try:
        # Fetch the vector
        fetched_vector = fetch_job_vector(test_job_id)
        
        # Compare vectors
        if len(fetched_vector) != len(expected_vector):
            print(f"Vector length mismatch. Expected {len(expected_vector)}, got {len(fetched_vector)}")
            return False
            
        # Convert to numpy arrays for comparison
        expected = np.array(expected_vector)
        fetched = np.array(fetched_vector)
        
        # Check if vectors are close (allowing for small floating-point differences)
        if np.allclose(expected, fetched):
            print("Test passed! Fetched vector matches expected vector")
            return True
        else:
            print("Test failed! Vectors do not match")
            return False
            
    except Exception as e:
        print(f"Error during test: {str(e)}")
        return False
    finally:
        # Clean up test data
        collection = Collection("jobs")
        collection.delete(f"job_id == {test_job_id}")
        print(f"Test job {test_job_id} cleaned up")

if __name__ == "__main__":
    test_fetch_job_vector() 