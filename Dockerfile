# Use a specific version tag for stability
FROM python:3.12-slim

# Prevent Python from buffering stdout/stderr (better logging)
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY . .

EXPOSE 5000

# Optimized Gunicorn for Docker
# --workers to utilize multiple cores
CMD ["gunicorn", \
     "--workers", "4", \
     "--worker-class", "gthread", \
     "--threads", "2", \
     "--worker-tmp-dir", "/dev/shm", \
     "--bind", "0.0.0.0:5000", \
     "app:app"]