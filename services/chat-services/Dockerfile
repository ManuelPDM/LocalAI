# Universal Dockerfile for Flask + Gunicorn services
FROM python:3.11-slim

WORKDIR /app

# Install Gunicorn first, as it's a common dependency
RUN pip install gunicorn

# Copy requirements file to leverage layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source code
COPY ./app .

# Expose the port the service will run on
EXPOSE 5002

# Use Gunicorn to run the application
# -w 4: Use 4 worker processes. Adjust as needed.
# -b 0.0.0.0:8000: Bind to all network interfaces on port 8000.
# main:app: Look for the 'app' object in the 'main.py' file.
CMD gunicorn -w ${WORKERS:-1} -b "0.0.0.0:$PORT" main:app