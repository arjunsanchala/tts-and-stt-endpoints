FROM python:3.9-slim

WORKDIR /

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Set environment variables
# ENV PYTHONDONTWRITEBYTECODE=1
# ENV PYTHONUNBUFFERED=1
# ENV FLASK_APP=app.py
# ENV FLASK_ENV=production

# Expose the port the app runs on
EXPOSE 8888

# Command to run the application
CMD ["python", "app.py"]