# Mini-Scan Processor

A scalable processor for network scan results that maintains an up-to-date record of discovered services.

## Prerequisites

- Docker and Docker Compose

## Quick Start

The `docker-compose.yml` file sets up a toy example of a scanner. It spins up:

- A Google Pub/Sub emulator
- A topic and subscription
- A scanner service that publishes mock scan results
- One or more processor instances

### Steps
1. Clone this repo
2. Run with:

```bash
docker compose up
```
Logging is enabled by default. After running the above command, you can view the stream in real-time:
![logging_screenshot.png](logging_screenshot.png)
The results are persisted in `data/scan_results.db`, which is created after the first run.

## Architecture
![architecture_diagram](architecture_diagram.png)
### Message Flow

1. Scanner publishes scan results to Pub/Sub topic 'scan-topic'
2. Processor(s) consume messages from subscription 'scan-sub'
3. Each message is validated and normalized
4. Results are stored in SQLite with composite key (ip, port, service)


### Message Processing Workflow
The processor implements a pipeline architecture where each stage handles a specific aspect of message processing, from validation to database operations. The workflow is designed with modularity in mind, allowing for potential future optimization.

Key components in the pipeline:
1. Message decoding and initial validation
2. Data extraction and normalization 
3. Version-specific response parsing
4. Database operations with atomic updates

The circular nodes in the workflow diagram represent processes that could be independently scaled if computationally intensive. For example, data validation or response parsing could be separated into their own services if they become bottlenecks. Similarly, the functions shown in blue (like `_validate_scan_data`, `_extract_scan_data`, `_parse_response`) are designed with clear boundaries that would allow them to be extracted into separate microservices or serverless functions if needed.

This modular design provides flexibility to optimize resource allocation based on workload characteristics while maintaining the simplicity of a single processor deployment for typical use cases.

![message_processing_workflow](message_processing_workflow.png)
### Horizontal Scaling

The processor achieves horizontal scaling through:

1. **Stateless Processing**: Each processor instance operates independently
2. **Thread-safe Database**: SQLite operations use transaction isolation
3. **Message Distribution**: Pub/Sub automatically distributes messages across processors
4. **Atomic Updates**: Database upserts prevent race conditions

Scale up processors:

```bash
docker compose up --scale processor=5
```

View processor logs:

```bash
docker compose logs -f processor
```

### At-Least-Once Delivery

The processor ensures reliable message processing:

1. Messages are only acknowledged after successful processing
2. Failed messages are automatically retried with exponential backoff
3. Transaction isolation prevents partial updates

## Dependencies

- `sqlalchemy`: ORM and database operations
- `google-cloud-pubsub`: Pub/Sub client
- `pytest`: Testing framework
- `ruff`: Linting and code style

## Development

Run unit tests:

```bash
pytest processor/tests/
```

Lint code:

```bash
ruff check .
```

## Production Considerations

For a production environment, consider:

- Replace SQLite with a distributed database
- Add metrics for message processing and latency tracking
- Implement dead-letter queue for failed messages
- Add monitoring and alerting
- Configure resource limits and auto-scaling
