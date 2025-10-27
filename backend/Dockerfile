# backend/Dockerfile
FROM python:3.11-slim

# Install system dependencies: QEMU and cloud-init tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    qemu-system-x86 \
    qemu-utils \
    cloud-image-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN mkdir -p /app/images
# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire backend source code
COPY . .

# Expose the API port
EXPOSE 8000

# Start the FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]