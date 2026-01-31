FROM python:3.11-slim

WORKDIR /app

# Install dependencies from launch_dam
COPY launch_dam/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code from launch_dam
COPY launch_dam/api ./api
COPY launch_dam/mcp ./mcp
COPY launch_dam/downloaders ./downloaders
COPY launch_dam/scripts ./scripts
COPY launch_dam/ingestion_spec.json .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
