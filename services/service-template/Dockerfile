# File: services/service-template/Dockerfile
# Universal Dockerfile for Flask + Gunicorn services

# Use a standard Python runtime.
FROM python:3.11-slim

# Set a build-time argument for the port with a default value.
ARG PORT=9000

# Set this argument as an environment variable available inside the container.
ENV PORT=$PORT

# Set the working directory.
WORKDIR /app

# Copy and install dependencies, leveraging layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source code.
COPY ./app .

# Expose the port. This is good practice for documentation and allows Docker
# to map the port dynamically if needed. It will use the value of $PORT.
EXPOSE $PORT

# The CMD now uses the $PORT environment variable. This makes the Dockerfile
# completely reusable for any service on any port.
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:$PORT", "main:app"]