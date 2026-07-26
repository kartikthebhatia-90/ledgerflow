FROM apache/superset:6.1.0

USER root
RUN pip install --no-cache-dir "duckdb-engine>=0.17,<1" "requests>=2.31,<3"
USER superset
