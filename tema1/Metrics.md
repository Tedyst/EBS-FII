# System Evaluation Report - Publish/Subscribe Network

This report provides an evaluation of the distributed publish/subscribe system based on RabbitMQ, analyzing its performance with 10,000 subscriptions using different equality operator frequencies.

## Test 1: 100% Equality Operators

### Test Configuration
- **Environment**: RabbitMQ message broker
- **Components**: 1 consumer, 2 filter workers, 1 aggregator, 1 producer
- **Duration**: 3 minutes continuous feed
- **Subscriptions**: 10,000 simple subscriptions
- **Equality Setting**: 100% (all fields use equality operator)

### Results

- **Publication Delivery Performance**

During the 3-minute test period, the system successfully delivered 19,009 publications through the broker network to the consumer. This represents a delivery rate of approximately 105.6 publications per second.

The producer generated 3,169 publications during the test period, which means many publications matched multiple subscriptions.

- **Latency Analysis**

The average latency (time from publication emission to receipt) measured across both filter workers:

| Filter Worker | Average Latency |
|---------------|----------------|
| Filter 1      | 226.78 ms      |
| Filter 2      | 243.66 ms      |
| **Overall**   | **235.22 ms**  |

This sub-quarter second latency demonstrates efficient message routing through the broker network even under load.

- **Matching Rate Analysis**

With 100% equality operators in subscription fields:

| Filter Worker | Matching Rate |
|---------------|--------------|
| Filter 1      | 1.22%        |
| Filter 2      | 1.32%        |
| **Overall**   | **1.27%**    |

This relatively low matching rate is expected with equality operators, as they require exact matches between publications and subscriptions.

## Test 2: 25% Equality Operators

### Test Configuration
- **Environment**: RabbitMQ message broker
- **Components**: 1 consumer, 2 filter workers, 1 aggregator, 1 producer
- **Duration**: 3 minutes continuous feed
- **Subscriptions**: 10,000 simple subscriptions
- **Equality Setting**: 25% (most fields use inequality operators, except city and direction which remained at 100%)

### Results

- **Publication Delivery Performance**

During the 3-minute test period, the system successfully delivered 209,997 publications through the broker network to the consumer. This represents a delivery rate of approximately 1,166.7 publications per second.

The producer generated 3,169 publications during the test period, indicating that publications matched significantly more subscriptions with inequality operators.

- **Latency Analysis**

The average latency (time from publication emission to receipt) measured across both filter workers:

| Filter Worker | Average Latency |
|---------------|----------------|
| Filter 1      | 7,096.77 ms    |
| Filter 2      | 6,908.56 ms    |
| **Overall**   | **7,002.67 ms**|

This higher latency (approx. 7 seconds) indicates the system is under significant load when processing inequality operators.

- **Matching Rate Analysis**

With 25% equality operators in subscription fields:

| Filter Worker | Matching Rate |
|---------------|--------------|
| Filter 1      | 14.23%       |
| Filter 2      | 13.94%       |
| **Overall**   | **14.09%**   |

This significantly higher matching rate shows how inequality operators drastically increase the number of matched subscriptions.

## Comparison and Analysis

### Publication Delivery
- **100% Equality**: 19,009 publications (105.6/second)
- **25% Equality**: 209,997 publications (1,166.7/second)
- **Increase**: 1,004.7%

### Latency
- **100% Equality**: 235.22 ms
- **25% Equality**: 7,002.67 ms
- **Increase**: 2,877.9%

### Matching Rate
- **100% Equality**: 1.27%
- **25% Equality**: 14.09%
- **Increase**: 1,010.2%

### Observations

1. **Matching Rate Impact**: Reducing the equality operator frequency from 100% to 25% increased the matching rate by approximately 10x, showing that inequality operators significantly expand the subscription matching space.

2. **System Load**: The substantial increase in latency (from ~235ms to ~7000ms) indicates that the system's processing capacity is heavily strained with inequality operators.

3. **Scalability Challenges**: While inequality operators provide more flexibility and higher matching rates, the nearly 30x increase in latency shows that the system requires significant optimization or additional resources to maintain acceptable performance.

4. **Performance Tradeoff**: There is a clear tradeoff between matching flexibility and system performance. Applications requiring low latency should favor equality operators, while those prioritizing higher match rates might accept the performance penalty of inequality operators.

5. **Aggregator Load**: The aggregator processed 9,040 messages with equality operators versus 85,555 with inequality operators - a ~9.5x increase, demonstrating the cascade effect of matching decisions on downstream components.

## Conclusion

The evaluation demonstrates that the choice of comparison operators in subscriptions dramatically impacts system performance. For systems requiring real-time or near-real-time performance, limiting the use of inequality operators or adding additional processing resources would be necessary to maintain acceptable latency levels.