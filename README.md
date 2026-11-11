# Databricks Asset Bundles

This repository contains Databricks Asset Bundle configuration and source code for the DEV workspace.

## Repository layout

- `databricks.yml`: bundle configuration and DEV target.
- `resources/snapshots_job.yml`: job definition for appending snapshot timestamps.
- `src/snapshots.py`: notebook that creates the managed Delta table if needed and appends one execution timestamp.

The job uses serverless compute and has no schedule, so it can be triggered manually during development.

## Deploy and run

From the repository root, with the Databricks CLI authenticated to the DEV workspace:

```sh
databricks bundle validate --target dev
databricks bundle deploy --target dev
databricks bundle run --target dev snapshots_job
```

The job identity needs permission to use catalog `datafact` and schema `data_model`, create the table, and insert rows.
