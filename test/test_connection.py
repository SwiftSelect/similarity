from milvus.connect import connect_to_milvus
import signal
from contextlib import contextmanager
import time

class TimeoutException(Exception):
    pass

@contextmanager
def timeout(seconds):
    def signal_handler(signum, frame):
        raise TimeoutException("Connection timed out")
    
    # Register a function to raise a TimeoutException on the signal
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        # Disable the alarm
        signal.alarm(0)

def test_connection():
    print("Attempting to connect to Zilliz Cloud...")
    try:
        with timeout(10):  # Set 10 second timeout
            start_time = time.time()
            connect_to_milvus()
            end_time = time.time()
            print(f"Successfully connected to Zilliz Cloud! (took {end_time - start_time:.2f} seconds)")
    except TimeoutException:
        print("Connection attempt timed out after 10 seconds. Please check your network connection and credentials.")
    except Exception as e:
        print(f"Connection failed: {str(e)}")
        print("Please verify your ZILLIZ_URI and ZILLIZ_TOKEN in the .env file.")

if __name__ == "__main__":
    test_connection() 