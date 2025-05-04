# run_all.py
import subprocess
import sys
import time
import signal
import os
import threading
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("service_launcher")

# Load environment variables
load_dotenv()

# Define the commands to run
commands = [
    {
        "name": "Embeddings API",
        "command": ["python3", "embeddings/embeddings-api.py"],
        "ready_message": "Uvicorn running on",
        "process": None
    },
    {
        "name": "Job Consumer",
        "command": ["python3", "-m", "candidate_matching.job_consumer"],
        "ready_message": "Starting job Kafka consumer for embeddings",
        "process": None,
        "depends_on": ["Embeddings API"]
    },
    {
        "name": "Candidate Consumer",
        "command": ["python3", "-m", "candidate_matching.candidate_consumer"],
        "ready_message": "Starting candidate Kafka consumer for embeddings",
        "process": None,
        "depends_on": ["Embeddings API"]
    },
    {
        "name": "Job Recommendations Consumer",
        "command": ["python3", "-m", "jobs_recommendation.consumer"],
        "ready_message": "Starting Job Recommendations Kafka consumer",
        "process": None,
        "depends_on": ["Embeddings API"]
    },
    {
        "name": "API for candidate-job matching and job recommendations",
        "command": ["python3", "main.py"],
        "ready_message": "Application startup complete",
        "process": None,
        "depends_on": []
    }
]

# Flag to track if shutdown was requested
shutdown_requested = False

# Function to read process output and detect when it's ready
def monitor_process(command_config, output_queue):
    process = command_config["process"]
    name = command_config["name"]
    ready_message = command_config["ready_message"]
    
    ready = False
    
    for line in iter(process.stdout.readline, b''):
        line_str = line.decode('utf-8').strip()
        logger.info(f"[{name}] {line_str}")
        
        # Check if the ready message is in the output
        if not ready and ready_message in line_str:
            ready = True
            output_queue.append(name)
            logger.info(f"✅ {name} is ready!")

def start_process(command_config, output_queue):
    name = command_config["name"]
    command = command_config["command"]
    
    logger.info(f"Starting {name}...")
    
    # Start the process with pipes for stdout and stderr
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        universal_newlines=False
    )
    
    command_config["process"] = process
    
    # Start a thread to monitor the process output
    monitor_thread = threading.Thread(
        target=monitor_process,
        args=(command_config, output_queue),
        daemon=True
    )
    monitor_thread.start()
    
    return process

# Handle graceful shutdown
def signal_handler(sig, frame):
    global shutdown_requested
    logger.info("Shutdown requested. Stopping all services...")
    shutdown_requested = True
    stop_all_processes()
    sys.exit(0)

def stop_all_processes():
    # Stop in reverse order
    for command_config in reversed(commands):
        if command_config["process"] is not None:
            logger.info(f"Stopping {command_config['name']}...")
            try:
                if sys.platform == 'win32':
                    command_config["process"].terminate()
                else:
                    command_config["process"].send_signal(signal.SIGTERM)
                command_config["process"].wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"Process {command_config['name']} didn't terminate gracefully, killing...")
                command_config["process"].kill()
            logger.info(f"Stopped {command_config['name']}")

# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def main():
    output_queue = []
    ready_services = set()
    
    try:
        # First, start services without dependencies
        for command_config in commands:
            if "depends_on" not in command_config or not command_config["depends_on"]:
                start_process(command_config, output_queue)
                time.sleep(2)  # Give a bit of time between service starts
        
        # Monitor the queue for services being ready
        while len(ready_services) < len(commands) and not shutdown_requested:
            # Check if any services reported as ready
            while output_queue:
                ready_service = output_queue.pop(0)
                ready_services.add(ready_service)
                
                # Check if any waiting services can now start
                for command_config in commands:
                    if command_config["process"] is None and "depends_on" in command_config:
                        if all(dep in ready_services for dep in command_config["depends_on"]):
                            start_process(command_config, output_queue)
                            time.sleep(2)  # Give a bit of time between service starts
            
            time.sleep(0.1)
        
        if not shutdown_requested:
            logger.info("✅ All services started successfully!")
            logger.info("Press Ctrl+C to stop all services")
            
            # Keep the main thread alive
            while not shutdown_requested:
                time.sleep(1)
                
                # Check if any process died unexpectedly
                for command_config in commands:
                    if command_config["process"] is not None:
                        if command_config["process"].poll() is not None:
                            logger.error(f"❌ {command_config['name']} exited unexpectedly with code {command_config['process'].poll()}")
                            logger.info("Shutting down all services...")
                            stop_all_processes()
                            return 1
    
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down all services...")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
    finally:
        stop_all_processes()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())