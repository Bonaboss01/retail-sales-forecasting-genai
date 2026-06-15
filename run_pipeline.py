# run_pipeline.py
#
# Submits the compiled pipeline (sfs_pipeline.json) to Vertex AI Pipelines
# and runs it.
#
# This is the step that actually executes your container on GCP --
# no Docker, no local machine needed from here on.
#
# Usage:
#   python3 run_pipeline.py

from google.cloud import aiplatform

PROJECT_ID = "sfs-dev-498722"
REGION = "europe-west2"
PIPELINE_ROOT = "gs://sfs-dev-pipeline-root"

# Initialize the Vertex AI SDK with your project and region
aiplatform.init(project=PROJECT_ID, location=REGION)

# Create a Pipeline Job from the compiled JSON
job = aiplatform.PipelineJob(
    display_name="sfs-data-pipeline-run",
    template_path="sfs_pipeline.json",
    pipeline_root=PIPELINE_ROOT,
    enable_caching=False,  # always run fresh, don't reuse cached results
)

# Submit and run the pipeline
job.run()

print("Pipeline submitted. Check Vertex AI Pipelines in the GCP Console for progress.")