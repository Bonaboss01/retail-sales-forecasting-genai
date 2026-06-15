# Week 3 Notes — Vertex AI Pipelines (Automated Data Pipeline)

## The Big Picture

Before today, your pipeline only ran when YOU typed a command on your Mac.

After today, GCP runs it automatically, on a schedule, using infrastructure you don't manage.

```
BEFORE:  You -> docker run -> your script -> BigQuery
AFTER:   Cloud Scheduler -> Vertex AI -> your container -> BigQuery
                                                            (every Saturday 7am)
```

---

## Key Concepts (the "why" behind each file)

### 1. `pipeline.py` — defines WHAT to run

- A "pipeline" = one or more steps (components)
- A "component" = one step. Ours wraps your existing Docker image
  (same image from Artifact Registry — nothing new built here)
- `@dsl.container_component` — tells Vertex AI: "run THIS image, with THIS command"
- `@dsl.pipeline` — wraps components into a pipeline
- Compiling turns this Python definition into `sfs_pipeline.json`
  — a format Vertex AI understands

**One-line summary:** *"This file describes my pipeline's structure as code."*

---

### 2. `run_pipeline.py` — runs it ONCE, manually

- Used for testing
- `aiplatform.PipelineJob(...)` = "create a job using this template"
- `pipeline_root` = a GCS bucket where Vertex AI stores logs/artifacts for each run
- `job.run()` = submit and execute now

**One-line summary:** *"This file says: run my pipeline right now, and show me the result."*

---

### 3. `create_schedule.py` — runs it AUTOMATICALLY, forever

- `job.create_schedule(...)` creates a persistent **Schedule** resource
- `cron="TZ=Europe/London 0 7 * * 6"` = every Saturday at 7am UK time
- `max_concurrent_run_count=1` = never run two copies at once

**One-line summary:** *"This file tells Vertex AI: run this pipeline every Saturday, forever, without me."*

---

## The 3 Real Bugs We Fixed (interview gold)

### Bug 1: Apple Silicon vs amd64 (architecture mismatch)

**Error:** `no matching manifest for linux/amd64`

**Cause:** Mac M-series chips build Docker images for `arm64` by default.
Vertex AI (and most cloud servers) run on `amd64`.

**Fix:**
```bash
docker build --platform linux/amd64 -f docker/Dockerfile.pipeline -t sfs-pipeline:latest .
```

**How to explain it:** *"I hit an architecture mismatch between my local
Apple Silicon build and the cloud's amd64 requirement — fixed by specifying
the target platform explicitly in the build step."*

---

### Bug 2: Service account couldn't access GCS bucket

**Error:** `does not have storage.objects.get permission to the bucket`

**Cause:** Vertex AI runs pipelines using a **service account**
(`<project-number>-compute@developer.gserviceaccount.com`), not your
personal account. It needs its own permissions.

**Fix:**
```bash
gcloud storage buckets add-iam-policy-binding gs://sfs-dev-pipeline-root \
  --member="serviceAccount:<project-number>-compute@developer.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

**How to explain it:** *"Vertex AI runs under a service account that needs
explicit IAM permissions — separate from my own user permissions."*

---

### Bug 3: BigQuery schema auto-detection (INT64 vs STRING)

**Error:** `Value has type INT64 which cannot be inserted into column
promo_type, which has type STRING`

**Cause:** When a column (e.g. `promo_type`) is entirely `None` for a batch
(no promotions that week), BigQuery's schema auto-detection can guess the
wrong type (INT64) for that all-null column — causing a mismatch with the
existing STRING column.

**Fix:** Explicitly cast nullable string columns before upload:
```python
for col in ["promo_type", "restriction_type", "restriction_reason", "restriction_severity"]:
    if col in df.columns:
        df[col] = df[col].astype("string")
```

**How to explain it:** *"I hit a subtle BigQuery schema auto-detection bug
where all-null columns get mis-typed — fixed by explicitly casting column
dtypes before upload, rather than relying on inference."*

---

## Permission Roles Reference

| Role | What it allows | Who needs it |
|---|---|---|
| BigQuery Data Viewer | Read table data | Team members (Power BI/Jupyter) |
| BigQuery Job User | Run queries | Team members (Power BI/Jupyter) |
| Storage Object Admin (on pipeline bucket) | Read/write pipeline artifacts | Vertex AI service account |

---

## Data Pipeline Safety Notes

- Your `upload_to_bigquery()` function uses `MERGE ... WHEN NOT MATCHED THEN INSERT`
  — re-running the pipeline will NOT create duplicate rows
- The state file (`.pkl`) is baked into the Docker image at build time —
  each scheduled run starts from that snapshot, not from the previous
  scheduled run's end state. New dates still get added correctly (MERGE
  prevents duplicates), but the "simulation memory" (inventory levels etc.)
  doesn't perfectly continue between automated runs.
- **Future improvement (not urgent):** persist the state file to GCS so
  each run truly continues from the last.

---

## Vertex AI Console Navigation (post-rebrand)

GCP rebranded "Vertex AI" to **"Agent Platform"** in the console UI.
Pipelines now live at:

```
Agent Platform -> Models -> Pipelines -> Runs / Schedules
```

URL pattern:
```
console.cloud.google.com/agent-platform/pipelines/locations/europe-west2/...
```

---

## The One-Sentence Summary for Interviews

*"My SFS data pipeline runs in a Docker container stored in Artifact Registry,
orchestrated by Vertex AI Pipelines, and triggered automatically every
Saturday via a native Vertex AI schedule — writing fresh synthetic retail
data into BigQuery with no manual intervention."*
