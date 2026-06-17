# Real-World Use Cases

Short scenarios where this telemetry pipeline fits production-style workloads.

## Industrial predictive maintenance

Factories stream vibration, temperature, and pressure readings from pumps, motors, and conveyors over MQTT or Kafka. The pipeline validates sensor payloads, stores high-frequency history in TimescaleDB, and flags bearing wear or overheating via the statistical + isolation-forest ensemble before equipment fails. Slack alerts route to on-call maintenance with device, severity, and drift context.

## Fleet and vehicle telematics

Logistics and rental fleets publish GPS-adjacent metrics (speed, engine temp, fuel, idle time) from thousands of vehicles. Kafka ingestion and horizontal scaling absorb burst traffic; windowed aggregates summarize trips and idle periods; rule-based thresholds catch unsafe or inefficient patterns. Grafana dashboards give ops teams a live fleet health view without building a custom analytics stack.

## Smart building and HVAC monitoring

Building management systems send temperature, humidity, and airflow data from zones and AHUs. MQTT fits lightweight edge gateways; tumbling windows roll up comfort and energy KPIs per floor or tenant. Anomalies surface stuck dampers, sensor faults, or runaway heating loops early enough to fix before occupant complaints or energy waste add up.

## Multi-tenant SaaS observability

A B2B platform ingests per-customer device telemetry with tenant-scoped API keys, Kafka topics, and Prometheus labels. Each tenant sees only their events and anomalies through the HTTP API; operators scale ingestion independently as customers grow. This pattern mirrors how product teams ship embedded IoT without commingling customer data.

## Manufacturing quality and process control

Production lines emit multi-metric snapshots per unit (dimensions, torque, cycle time). Schema validation rejects malformed PLC exports; enrichment tags lines, shifts, and SKUs for downstream analysis. Spikes and flatlines in critical fields trigger alerts so bad batches are stopped before they leave the line.

## Energy and utilities grid monitoring

Substations and renewable sites report voltage, frequency, and inverter metrics at sub-second rates. TimescaleDB retention and compression policies keep months of history queryable; ADWIN drift detection spots gradual degradation (panel soiling, transformer aging) that fixed thresholds miss. Replay mode replays historical CSV incidents for model tuning and post-mortems.

## Network and infrastructure telemetry

NOC teams ingest router, switch, and host metrics (latency, packet loss, CPU) as synthetic “sensor” events. The same anomaly ensemble used for physical sensors applies to operational metrics—useful when you want one pipeline for OT and IT signals. Prometheus and Grafana tie pipeline health to the metrics being monitored.

## ML model evaluation and labeling

Teams use the synthetic generator and NAB/pump CSV replay to inject known anomalies at controlled rates, then run `telemetry-eval` and threshold sweeps against labeled data. Per-sensor ONNX models and Grafana ML dashboards support comparing statistical vs. autoencoder performance before promoting models to production inference.

## Capacity planning and load testing

Before a product launch or Black Friday traffic, engineers run `telemetry-load` and Kafka producer floods at 100k+ eps against staging clusters. Results show whether Redpanda partitions, pipeline replicas, and TimescaleDB batching can sustain target volume—without waiting for real user traffic to expose bottlenecks.

## Edge-to-cloud staging and CI validation

Developers point the simulator at a local or Docker Compose stack to verify schema changes, new sensor types, and alert rules before deploy. GitHub Actions smoke tests and Helm/ArgoCD GitOps flows keep the same config validated from laptop through Kubernetes, reducing surprises when real devices connect in the field.