# Databricks Asset Bundles

This repository contains Databricks Asset Bundle configuration and source code for the DEV workspace.

## Repository layout

- `databricks.yml`: bundle configuration and DEV target.
- `resources/`: job and other Databricks resource definitions.
- `src/`: notebooks and source code deployed by the bundle.

The initial job will write one timestamp row to a table on each run.
