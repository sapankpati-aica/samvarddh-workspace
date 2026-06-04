FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Create all required data directories
RUN mkdir -p /app/samvarddh_data/uploads/designs \
    /app/samvarddh_data/uploads/procurement \
    /app/samvarddh_data/uploads/setup \
    /app/samvarddh_data/reports \
    /app/samvarddh_data/backups

# Set environment variables
ENV DATA_DIR=/app/samvarddh_data
ENV PYTHONPATH=/app

# Move into backend directory and start
WORKDIR /app/backend
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
