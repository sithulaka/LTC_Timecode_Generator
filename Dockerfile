FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir numpy
COPY ltc_generator.py cli.py ./
ENTRYPOINT ["python", "cli.py"]
