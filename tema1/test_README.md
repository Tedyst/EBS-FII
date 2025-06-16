# Tests for Matching and Aggregation

This directory contains tests for the matching and aggregation modules used in the pub/sub system.

## Test Files

- `test_matching.py`: Tests for the filtering and matching mechanisms
- `test_aggregation.py`: Tests for aggregation mechanisms

## Running Tests

You can run the tests using either unittest or pytest.

### Using unittest

```bash
# To run all tests
python -m unittest discover

# To run a specific test file
python -m unittest test_matching.py
python -m unittest test_aggregation.py
```

### Using pytest

If you have pytest installed:

```bash
# Install pytest if needed
pip install pytest

# Run all tests
pytest

# Run a specific test file
pytest test_matching.py
pytest test_aggregation.py

# Run with verbose output
pytest -v
```

## Test Coverage

The tests cover:

### Matching tests
- `ComparableFilter`: Testing simple equality and other comparison matchers
- `AllComparableFilter`: Testing composite filters that handle all comparison types

### Aggregation tests
- `AggregationFilter`: Testing various aggregation functions (AVG, SUM, MIN, MAX)
- `Aggregator`: Testing the complete aggregation mechanism with window-based aggregations
