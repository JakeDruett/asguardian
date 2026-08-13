# Synthetic Dockerfile for benchmark workloads. Never built.
FROM python:3.11
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt
ENV API_TOKEN=fake-benchmark-token
EXPOSE 8080
CMD ["python", "-m", "app.main"]
