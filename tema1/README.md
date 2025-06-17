# Parameters Used

    Number of Publications: 10,000; 20,000; 50,000
    Number of Subscriptions: 10,000; 20,000; 50,000
    Number of Processes: 2, 4, 8, 16
    Number of Threads: 1, 2, 4

# Processor Specifications:

## Dan:

AMD Ryzen 5 4500U

- 6 Cores
- 6 Threads
- 15 W TDP
- 2.3 GHz Frequency
- 4 GHz Boost

### CPU:

Info: 6-core model: AMD Ryzen 5 4500U with Radeon Graphics bits: 64
type: MCP cache: L2: 3 MiB
Speed (MHz): avg: 1397 min/max: 1400/2375 cores: 1: 1397 2: 1397 3: 1397
4: 1397 5: 1397 6: 1397

### Results:

![fire-de-executie](graphs/Dan/threads_execution_time.png)
![procese](graphs/Dan/processes_execution_time.png)
![publicatii](graphs/Dan/publications_execution_time.png)
![subscriptii](graphs/Dan/subscriptions_execution_time.png)

## Vlad:

Intel Core i7-8750H - 6 Cores - 12 Threads - 45 W TDP (Thermal Design Power) - 2.2 GHz Base Frequency - 4.1 GHz Turbo Boost

### CPU:

Info: 6-core model: Intel Core i7-8750H with Integrated Intel UHD Graphics 630 (45W) bits: 64
type: Mobile processor, cache: L2: 1.5 MiB, L3: 9 MiB
Speed (MHz): avg: 1397 min/max: 800/4100 cores: 1: 1397 2: 1397 3: 1397
4: 1397 5: 1397 6: 1397

### Results:

![fire-de-executie](graphs/Vlad/threads_execution_time.png)
![procese](graphs/Vlad/processes_execution_time.png)
![publicatii](graphs/Vlad/publications_execution_time.png)
![subscriptii](graphs/Vlad/subscriptions_execution_time.png)

# Publish/Subscribe System with RabbitMQ

## Project Overview

This project implements a distributed publish/subscribe system using RabbitMQ as the message broker. The system supports weather data publications with complex filtering and aggregation capabilities. Each publication contains weather information such as temperature, rainfall, wind speed, and direction for various cities and weather stations.

### Key Features

- **Content-based filtering**: Publications are matched against subscriptions based on their content
- **Complex subscription operators**: Supports equality, inequality, greater than, less than comparisons
- **Aggregation**: Supports aggregating values (MIN, MAX, AVG, SUM) over time windows
- **Distributed architecture**: Multiple filter workers can process publications in parallel
- **High performance**: Can handle thousands of publications and subscriptions

## System Architecture

The system consists of several components:

1. **Consumer**: Creates subscriptions and receives matched publications
2. **Filter Workers**: Process publications and match them against subscriptions
3. **Aggregator**: Performs time-window aggregations on publications
4. **Producer**: Generates and sends weather publications to the system

All components communicate through a RabbitMQ message broker.

## Running the System

### Prerequisites

- Python 3.8+
- Docker (for running RabbitMQ)
- Required Python packages (install with `poetry install`)

### 1. Start the RabbitMQ Server

```
docker run -d --hostname rabbitmqebs --name rabbitmqebs -e RABBITMQ_DEFAULT_USER=user -e RABBITMQ_DEFAULT_PASS=password -p 5672:5672 -p 5552:5552 -p 15692:15692 -p 15672:15672 rabbitmqebs
```

This starts a RabbitMQ server with:
- Username: `user`
- Password: `password`
- Management interface available at http://localhost:15672/
- AMQP port: 5672

If the container already exists, you can start it with:
```
docker start rabbitmqebs
```

### 2. Start the Consumer

```
python main_2.py consumer 1000
```

The consumer creates subscriptions and waits for matching publications. The parameter (10000) specifies the number of subscriptions to create.

### 3. Start the Filter Workers
```
python main_2.py filter all
```

This starts a filter worker that processes all fields (stationid, city, temp, rain, wind, direction, date).

You can run multiple filter workers to process publications in parallel, each in its own terminal:

### 4. Aggregator

```
python main_2.py aggregate all
```

The aggregator performs time-window aggregations on the publications. Similar to the filter, you can specify which fields to aggregate:

### 5. Generate Publications
```
python main_2.py create_pubs 1000
```
This generates and sends 1000 random weather publications to the system. You can adjust the number as needed.

### 6. Clearing the System

To clear all streams and queues:
```
python main_2.py clear
```

You can also specify individual fields to filter on:

This is useful when you want to start with a clean state.

## System Evaluation

The system has been evaluated with different configurations:

1. **100% equality operators**: All subscriptions use equality operators (==)
2. **25% equality operators**: Most subscriptions use inequality operators (>, <, !=)

The evaluation measured:
- Publication delivery rate
- Average latency
- Matching rate

Results are available in [Metrics.md](Metrics.md).

## Advanced Usage

### Running with Multiple Processes

This runs 4 filter worker processes in parallel.

### Configuring Subscription Generation

Subscription properties can be configured by modifying the `PONDERS` variable in `workers/consumer.py`.
