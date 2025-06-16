# Pub/Sub System Evaluation Results

## Test Configuration

- Test field for equality operator comparison: temp
- Evaluation period: 180.20 seconds
- Total subscriptions: 12000
  - 100% equality subscriptions: 5000
  - 25% equality subscriptions: 5000
  - Aggregation subscriptions: 2000
- Publications sent: 9000
- Start time: 2025-06-16 21:16:29.829193
- End time: 2025-06-16 21:19:30.030890

## Results

### a) Publication Delivery

- Total publications delivered: 357
- Publications delivered per second: 1.98
- Delivery success rate: 3.97%

### b) Latency

- Overall average latency: 0.00 ms
- 100% equality subscriptions latency: 0.00 ms
- 25% equality subscriptions latency: 0.00 ms
- Aggregation subscriptions latency: 0.00 ms

### c) Matching Rates

#### 100% Equality Operator

- Subscriptions: 5000
- Matched publications: 167
- Matching rate: 1.86%

#### 25% Equality Operator

- Subscriptions: 5000
- Matched publications: 190
- Matching rate: 2.11%

#### Aggregation

- Subscriptions: 2000
- Matched publications: 0
- Matching rate: 0.00%

#### Comparison

- Equality operator ratio (100% vs 25%): 0.88x
