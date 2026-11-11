# Databricks notebook source
# COMMAND ----------
# MAGIC %sql
# MAGIC CREATE TABLE IF NOT EXISTS datafact.data_model.snapshots (
# MAGIC   execution_timestamp TIMESTAMP NOT NULL
# MAGIC )
# MAGIC USING DELTA

# COMMAND ----------
# MAGIC %sql
# MAGIC WITH execution AS (
# MAGIC   SELECT current_timestamp() AS execution_timestamp
# MAGIC )
# MAGIC INSERT INTO datafact.data_model.snapshots (execution_timestamp)
# MAGIC SELECT execution_timestamp
# MAGIC FROM execution
