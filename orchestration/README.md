# Orchestration

Airflow 3.3.2 runs the pipeline every night: the extractor, then the `_live`
tables, then dbt, each as a container from our images.

- The DAG: [dags/marketplace_g04.py](dags/marketplace_g04.py)
- How to run it, and the evidence: [docs/orchestration.md](../docs/orchestration.md)
- When it fails: [docs/runbooks/failed-run.md](../docs/runbooks/failed-run.md)
- Why it is safe to rerun: [ADR 0007](../docs/adr/0007-idempotency.md)

`docker-compose.yaml` is Airflow's own, unchanged. Our changes are in
`docker-compose.override.yaml`; your paths and the alert webhook go in `.env`
(copy `.env.example`), which is never committed.
