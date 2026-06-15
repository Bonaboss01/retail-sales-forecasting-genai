# create_schedule.py
#
# Creates a recurring SCHEDULE for the SFS pipeline on Vertex AI.
# Unlike run_pipeline.py (which runs the pipeline ONCE, right now),
# this sets up automation: Vertex AI will run the pipeline
# automatically every week, with no manual trigger needed.
#
# Usage:
#   python3 create_schedule.py
#
# To check/manage schedules later:
#   GCP Console -> Vertex AI / Agent Platform -> Pipelines -> Schedules

from google.cloud import aiplatform

PROJECT_ID = "sfs-dev-498722"
REGION = "europe-west2"
PIPELINE_ROOT = "gs://sfs-dev-pipeline-root"

aiplatform.init(project=PROJECT_ID, location=REGION)

# Define the pipeline job template (this is NOT run immediately --
# it's used as the "blueprint" for each scheduled run)
job = aiplatform.PipelineJob(
    display_name="sfs-data-pipeline-run",
    template_path="sfs_pipeline.json",
    pipeline_root=PIPELINE_ROOT,
    enable_caching=False,
)

# Create the recurring schedule.
#
# cron format: "TZ=<timezone> <minute> <hour> <day> <month> <weekday>"
#   - weekday: 0=Sunday, 1=Monday, ... 6=Saturday
#   - "0 7 * * 6" = at 07:00, every Saturday
#   - TZ=Europe/London ensures this is UK time (handles BST/GMT automatically)
#
# max_concurrent_run_count=1 -- never run two copies at once
# max_run_count=None         -- run indefinitely (no end date)

pipeline_job_schedule = job.create_schedule(
    display_name="sfs-weekly-schedule",
    cron="TZ=Europe/London 0 7 * * 6",
    max_concurrent_run_count=1,
    max_run_count=None,
)

print("Schedule created successfully!")
print(f"Resource name: {pipeline_job_schedule.resource_name}")
print("The pipeline will now run automatically every Saturday at 7am UK time.")