#!/bin/bash

# Helper function to kill worker processes
cleanup() {
    echo "Cleaning up worker processes..."
    if [ ! -z "$FILTER_PID" ]; then
        kill $FILTER_PID 2>/dev/null
    fi
    if [ ! -z "$AGGREGATOR_PID" ]; then
        kill $AGGREGATOR_PID 2>/dev/null
    fi
    exit 0
}

# Set up cleanup on script exit
trap cleanup EXIT INT TERM

echo "=== Pub/Sub System Complete Evaluation ==="

# Check if Python environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Warning: No virtual environment detected"
    echo "Make sure dependencies are installed"
    echo ""
fi

# Make sure the Python script exists and is executable
if [ -f "test_system.py" ]; then
    chmod +x test_system.py
else
    echo "Error: test_system.py not found"
    exit 1
fi

# Purge RabbitMQ queues before starting
echo "Clearing RabbitMQ queues..."
docker exec rabbitmqebs rabbitmqctl purge_queue EVAL_TOPIC_100PCT || true
docker exec rabbitmqebs rabbitmqctl purge_queue EVAL_TOPIC_25PCT || true
docker exec rabbitmqebs rabbitmqctl purge_queue EVAL_TOPIC_AGGREGATION || true

echo "Starting filter worker..."
# Start filter worker in background
echo "Starting filter worker..."
python main_2.py filter all > filter_worker.log 2>&1 &
FILTER_PID=$!
echo "Filter worker started with PID: $FILTER_PID"

# Start aggregator worker in background
echo "Starting aggregator worker..."
python main_2.py aggregate all > aggregator_worker.log 2>&1 &
AGGREGATOR_PID=$!
echo "Aggregator worker started with PID: $AGGREGATOR_PID"

# Wait for workers to initialize
echo "Waiting for workers to initialize..."
sleep 5

# Run the evaluation with provided args
echo "Starting comprehensive system evaluation..."
python test_system.py "$@"

echo "Evaluation completed. Shutting down workers..."