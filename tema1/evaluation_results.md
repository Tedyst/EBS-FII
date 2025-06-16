# Pub/Sub System Evaluation Results

## Test Configuration

- Test field for equality operator comparison: temp
- Evaluation period: 180.17 seconds
- Total subscriptions: 10000
  - 100% equality subscriptions: 5000
  - 25% equality subscriptions: 5000
- Publications sent: 3600
- Start time: 2025-06-16 20:04:48.200613
- End time: 2025-06-16 20:07:48.370175

## Results

### a) Publication Delivery

- Total publications delivered: 4694
- Publications delivered per second: 26.05
- Delivery success rate: 130.39%

### b) Latency

- Overall average latency: 0.00 ms
- 100% equality subscriptions latency: 0.00 ms
- 25% equality subscriptions latency: 0.00 ms

### c) Matching Rates

#### 100% Equality Operator

- Subscriptions: 5000
- Matched publications: 2204
- Matching rate: 61.22%

#### 25% Equality Operator

- Subscriptions: 5000
- Matched publications: 2490
- Matching rate: 69.17%

#### Comparison

- Equality operator ratio (100% vs 25%): 0.89x
