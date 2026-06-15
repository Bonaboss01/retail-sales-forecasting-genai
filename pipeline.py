# pipeline.py
#
# Defines a Vertex AI Pipeline that runs the sfs-pipeline container
# (generate_upload_to_bigquery.py) from Artifact Registry.
#
# This file does TWO things:
#   1. Defines the pipeline structure (what container to run)
#   2. Compiles it into a JSON file that Vertex AI can execute
#
# Usage:
#   python3 pipeline.py
#
# This creates: sfs_pipeline.json
# That file is then submitted to Vertex AI in a separate step (run_pipeline.py)

from kfp import dsl
from kfp import compiler


# =========================================================
# COMPONENT
# =========================================================
# A "component" is one step in a pipeline.
# Here, our component simply runs our existing Docker image
# from Artifact Registry — the same image we built and pushed
# in Week 2.

@dsl.container_component
def run_sfs_data_pipeline():
    return dsl.ContainerSpec(
        image="europe-west2-docker.pkg.dev/sfs-dev-498722/sfs-pipeline/sfs-pipeline:latest",
        command=["python", "generate_upload_to_bigquery.py"],
    )


# =========================================================
# PIPELINE
# =========================================================
# A "pipeline" is a sequence of components.
# Right now we only have ONE step — but this structure is
# what allows you to add more steps later (e.g. training,
# evaluation, feature engineering).

@dsl.pipeline(
    name="sfs-data-pipeline",
    description="Runs the SunnyX SFS synthetic data generator and uploads to BigQuery",
)
def sfs_pipeline():
    run_sfs_data_pipeline()


# =========================================================
# COMPILE
# =========================================================
# Compiling converts the Python pipeline definition above
# into a JSON file that Vertex AI understands and can execute.

if __name__ == "__main__":
    compiler.Compiler().compile(
        pipeline_func=sfs_pipeline,
        package_path="sfs_pipeline.json",
    )
    print("Pipeline compiled successfully -> sfs_pipeline.json")