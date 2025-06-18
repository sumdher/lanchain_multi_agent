# FROM python:3.12-slim

# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#     python3-pip \
#     curl \
#     && apt-get clean \
#     && rm -rf /var/lib/apt/lists/*

# RUN pip install python-multipart fastapi uvicorn jupyter-client nbformat ipykernel
# RUN python3 -m ipykernel install --user
# RUN pip install pandas numpy matplotlib scipy seaborn scikit-learn pyarrow tabulate openpyxl xlrd

# RUN mkdir -p /mnt/data /mnt/jupyter_sessions /workspace

# ENV DATA_DIR=/mnt/data
# ENV JUPYTER_SESSIONS_DIR=/mnt/jupyter_sessions

# COPY sandbox.py /workspace/sandbox.py

# WORKDIR /workspace

# EXPOSE 5002

# CMD ["python3.12", "-m", "uvicorn", "sandbox:app", "--host", "0.0.0.0", "--port", "5002"]









# ───────────────────────── base image ─────────────────────────
FROM python:3.12-slim AS runtime

# ——— Native deps (Java for Spark, basic build tools) ———
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openjdk-17-jre-headless \
        build-essential \
        curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ——— Python libraries ———
RUN pip install --no-cache-dir \
        python-multipart fastapi uvicorn \
        jupyter-client nbformat ipykernel \
        pandas numpy matplotlib scipy seaborn scikit-learn pyarrow tabulate \
        openpyxl xlrd pyspark docker

# ——— Create non-root user and workspace dirs ———
RUN useradd --create-home --shell /bin/bash sandbox && \
    mkdir -p /mnt/data /mnt/jupyter_sessions /workspace && \
    chown -R sandbox:sandbox /mnt/data /mnt/jupyter_sessions /workspace

USER sandbox
WORKDIR /workspace

ENV DATA_DIR=/mnt/data
ENV JUPYTER_SESSIONS_DIR=/mnt/jupyter_sessions
ENV PYSPARK_PYTHON=python3.12
ENV PYSPARK_DRIVER_PYTHON=python3.12

COPY --chown=sandbox:sandbox sandbox.py /workspace/sandbox.py

# FastAPI (5002) + Spark-UI defaults (4040 driver, 4041 executor-0)
EXPOSE 5002 4040 4041

CMD ["python3.12", "-m", "uvicorn", "sandbox:app", "--host", "0.0.0.0", "--port", "5002"]
