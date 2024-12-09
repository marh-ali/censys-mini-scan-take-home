FROM python:3.12-slim

WORKDIR /app

# Create data directory
RUN mkdir -p /app/data

COPY processor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY processor/ processor/

# Run the processor
CMD ["python", "-m", "processor"]