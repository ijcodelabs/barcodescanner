FROM python:3.14-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api.py .

# Set environment variables
ENV FLASK_ENV=production \
    LOG_LEVEL=INFO \
    PYTHONUNBUFFERED=1

# Expose the port the app runs on
EXPOSE 5000

# Run the application
CMD ["python", "api.py"]
