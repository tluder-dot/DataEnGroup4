# Runbook: the nightly pipeline failed

For whoever is on call at 3:00 and did not build it. Go in order.

## 1. How do I know?

A message in the Discord channel **`#pipeline-alerts`**:

```
ALERT g04_marketplace_daily.<task> failed for <date> after 3 tries. Runbook: docs/runbooks/failed-run.md
```

It names the task, and the day the run covers. It is sent once, after the
task's third attempt, so the task has already retried twice, 2 minutes apart.
The same line is in the task's log. Nothing else alerts: if Kafka or the
consumer stops, no message comes (see the end).

## 2. What do I look at first?

| Where | How |
|---|---|
| The UI | http://localhost:8080, user `airflow`, DAG `g04_marketplace_daily`, **Grid**: the red square, then **Logs** |
| The log on disk | `orchestration/logs/dag_id=g04_marketplace_daily/run_id=<run>/task_id=<task>/attempt=3.log`. The cause is in the last 30 lines |
| The failed container | `docker ps -a --filter status=exited`: a failed task's container is kept, read it with `docker logs <name>` |
| The state of every task | `cd orchestration && docker compose exec -T airflow-scheduler airflow tasks states-for-dag-run g04_marketplace_daily <run_id>` |

## 3. The usual breakages

Each one happened this week.

### A · Credentials: `Forbidden ... The billing account for the owning project is disabled`

**Seen:** 18 November 18:57 (all seven extracts) and 19 November 12:20 (the
consumer, 16 failures in 3 minutes).

**It is not the course's billing.** The message names the project *billed* for
the call, which the application default credentials (ADC) take from their
"quota project". Ours pointed at another project of Jane's,
`agentics-workflows-510809`, whose billing is off. A write with `gcloud storage
cp` worked at the same time, because it does not send that project.

**Check:**
```
python3 -c "import json,os; d=json.load(open(os.path.expanduser('~/.config/gcloud/application_default_credentials.json'))); print(d.get('quota_project_id'))"
gcloud config get-value project
```
**Fix:** both must say `data-engineering-i1`:
```
gcloud config set project data-engineering-i1
gcloud auth application-default set-quota-project data-engineering-i1
docker restart group4-consumer-clickstream-1
```
Then rerun (section 4). Same family: `Reauthentication required` or
`RefreshError` means the Google login expired: `gcloud auth application-default
login`, then rerun.

### B · Memory: a container `Exited (137)`

**Seen:** 18 November, about 19:00: Kafka, the Airflow worker and the
triggerer killed. The run froze, and Kafka stayed down for about 18 hours.

**Check:** `docker ps -a --format '{{.Names}}  {{.Status}}'` (137 means
killed) and `memory_pressure | tail -1` (below 20 % free, the Mac is short).

**Fix:** close the other apps; stop what is not the pipeline (other Compose
projects); restart the shop stack (`docker compose up -d` in
`albert-marketplace`) and Airflow without the triggerer (see
[docs/orchestration.md](../orchestration.md#run-it)). Then rerun.

### C · Bad data: `dbt_build` failed with `FAIL` on a test

**Seen:** 19 November, the gate drill: `FAIL 1 not_null_stg_orders_buyer_id`.

**This is the gate doing its job.** Gold was not touched: it still holds the
last good build. **Do not just rerun:** the same row fails the same test.

**Fix:** find the row the test names (here, an order with no buyer), tell Till
(silver and gold are his models), and decide with him: fix the source, or
change the rule. Then rerun.

### Also check

- **A vanished image tag**: `manifest unknown` or `pull access denied` in the
  log. The tag in the DAG (`TAG = ...`) must exist on Docker Hub,
  `jgalthie/group4-ingestion` and `jgalthie/group4-transform`. Tags are never
  deleted while the DAG uses them ([ADR 0006](../adr/0006-image-registry-and-tags.md)).
- **A moved source**: `could not translate host name "db"` means the shop stack
  is down or on another network (`albert-marketplace_default`).

## 4. Is it safe to just rerun?

**Yes, for A and B, once the cause is fixed.** Every task replaces what it
writes instead of adding to it ([docs/orchestration.md](../orchestration.md#idempotency),
measured: two reruns gave the same counts). Rerun only the failed task and
what follows:

```
cd orchestration
docker compose exec -T airflow-scheduler airflow tasks clear g04_marketplace_daily -t "^<task>$" --downstream -s <date> -e <date+1> --yes
```

Watch the dates: `-e` must be the day **after**, or nothing is cleared (a
daily run is stamped 02:00).

**No, for C**, until the data is fixed.

## 5. Who to tell, and when to stop

| When | Tell |
|---|---|
| Always, once it is fixed | The group channel: what broke, what you did |
| A test failed (C) | Till: silver and gold |
| `Forbidden` comes back after the fix in A, with `quota project` right | Charles: it may then be the course project |
| Kafka or the consumer was down for more than a day | Jane: events may be lost past 7 days (ADR 0003) |

**Stop** after two reruns that fail the same way: do not loop. Leave the run
red, write down the time and the error, and tell the group.

## The drill that confirms it

On 19 November, the gate drill was handled with this page: the alert named
`dbt_build` (section 1); the log showed `FAIL 1 not_null_stg_orders_buyer_id`
(section 2); breakage C said not to rerun first; the row was deleted, the run
cleared (section 4), and it went green again, 13:15:56 to 13:18:03. Details in
[docs/orchestration.md](../orchestration.md#the-quality-gate).
