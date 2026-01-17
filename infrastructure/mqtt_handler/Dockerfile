FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mqtt_standalone.py .

# Run MQTT handler
CMD ["python", "mqtt_standalone.py"]
