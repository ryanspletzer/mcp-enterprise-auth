FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy client code
COPY client.py .

# Make executable
RUN chmod +x client.py

# Run client
CMD ["python", "client.py"]
