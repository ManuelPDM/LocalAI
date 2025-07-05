# This Dockerfile is for the MAIN WEB APP

FROM python:3.11-slim
WORKDIR /app

# Copy the requirements file for the main app
COPY requirements.txt .

# Install dependencies for the main app
RUN pip install --no-cache-dir -r requirements.txt

# Copy the main application files
COPY . .

# Expose the port for the main app
EXPOSE 8000

# Command to run the main app
CMD ["python", "app.py"]