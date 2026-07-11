#!/bin/bash
# run_pipeline.sh

# Ensure python path is set to the current directory
export PYTHONPATH="."

echo "====================================================="
echo "  PRAVAH Stage 1-3 Pipeline Execution"
echo "====================================================="
echo ""

echo "1. Running Data Ingestion & DB Upserts..."
python shared/clients/test_spine.py
if [ $? -ne 0 ]; then
  echo "Data Ingestion completed with some failures."
else
  echo "Data Ingestion completed successfully."
fi
echo ""

echo "2. Rebuilding Knowledge Graph from DB..."
python shared/db/knowledge_graph.py
if [ $? -ne 0 ]; then
  echo "Knowledge Graph build failed."
else
  echo "Knowledge Graph built successfully."
fi
echo ""

echo "3. Running Integration Tests..."
python -m pytest shared/clients/test_integration.py -v
if [ $? -ne 0 ]; then
  echo "Integration Tests failed."
else
  echo "Integration Tests passed successfully."
fi
echo ""

echo "====================================================="
echo "  Pipeline Execution Complete"
echo "====================================================="
