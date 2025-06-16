#!/bin/bash
# filepath: /home/dan/Documents/Master_S2/Sisteme bazate pe evenimente/Proiect/EBS-FII/tema1/evaluate_system.sh

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

echo "=== Pub/Sub System Evaluation ==="

# Check if Python environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Warning: No virtual environment detected"
    echo "Make sure dependencies are installed"
    echo ""
fi

# Make sure the Python script exists and is executable
if [ -f "evaluate_system.py" ]; then
    chmod +x evaluate_system.py
else
    echo "Error: evaluate_system.py not found"
    exit 1
fi

# Start filter worker in background
echo "Starting filter worker..."
python main_2.py filter all &
FILTER_PID=$!
echo "Filter worker started with PID: $FILTER_PID"

# Start aggregator worker in background
echo "Starting aggregator worker..."
python main_2.py aggregate all &
AGGREGATOR_PID=$!
echo "Aggregator worker started with PID: $AGGREGATOR_PID"

# Wait for workers to initialize
echo "Waiting for workers to initialize..."
sleep 5

# Run the evaluation with provided args
echo "Starting evaluation..."
python evaluate_system.py "$@"

# Show results if available
if [ -f "evaluation_results.md" ]; then
    echo ""
    echo "=== Results Summary ==="
    head -n 20 evaluation_results.md
    echo "..."
    echo "Full results available in evaluation_results.md"
fi

# Cleanup happens automatically via the trap
echo "Evaluation completed. Shutting down workers..."