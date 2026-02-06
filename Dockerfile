# Build stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed for some libraries)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set environment variable for Python to run in unbuffered mode (logs show up immediately)
ENV PYTHONUNBUFFERED=1

# Command to run the bot
CMD ["python", "irispy.py"]
