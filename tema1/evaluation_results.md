# Pub/Sub System Evaluation Results

## Test Configuration

- Test field for equality operator comparison: temp
- Evaluation period: 120.04 seconds
- Total subscriptions: 10000
  - 100% equality subscriptions: 5000
  - 25% equality subscriptions: 5000
- Publications sent: 1800
- Start time: 2025-06-16 20:56:11.551618
- End time: 2025-06-16 20:58:11.591369

## Results

### a) Publication Delivery

- Total publications delivered: 82928
- Publications delivered per second: 690.84
- Delivery success rate: 4607.11%

### b) Latency

- Overall average latency: 0.00 ms
- 100% equality subscriptions latency: 0.00 ms
- 25% equality subscriptions latency: 0.00 ms

### c) Matching Rates

#### 100% Equality Operator

- Subscriptions: 5000
- Matched publications: 39130
- Matching rate: 2173.89%

#### 25% Equality Operator

- Subscriptions: 5000
- Matched publications: 43798
- Matching rate: 2433.22%

#### Comparison

- Equality operator ratio (100% vs 25%): 0.89x
