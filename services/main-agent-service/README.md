# Microservice Template

## Overview

This directory serves as a standardized template for creating new Python-based microservices within the project. It includes a production-ready setup with Flask and Gunicorn, configured to integrate seamlessly with the existing Docker and Traefik architecture.

By following the steps below, you can quickly bootstrap a new service, ensuring consistency and reducing boilerplate setup.

---

## How to Create a New Service from This Template

Follow these steps to turn this template into a new, running microservice.

### Step 1: Make Key Decisions

Before you start, decide on the following three unique identifiers for your new service:

1.  **Service Name:** A unique, lowercase, hyphenated name (e.g., `document-parser`).
2.  **API Route:** The unique URL path for your service's main endpoint (e.g., `parse-document`). This will be accessible at `/api/<your-api-route>`.
3.  **Port:** A unique port number that is not used by any other service (e.g., `5003`).

### Step 2: Copy This Template Directory

From the project's **root directory**, copy this entire `service-template` directory and rename it to your chosen service name.

```bash
# Example for a service named 'document-parser'
cp -r services/service-template services/document-parser
```

### Step 3: Implement Your Service Logic

Navigate into your new service directory (`services/<your-service-name>/`) and edit the following files:

1.  **`app/main.py`**:
    -   Locate the `@app.route()` decorator.
    -   Change the route from `/api/template-route` to `/api/<your-api-route>`.
    -   Write your service's core logic inside the handler function.
    -   If your service needs to communicate with other services (like `core-service`), use the provided `os.getenv()` examples. You will need to add the required environment variables in the `docker-compose.yml` file in the next step.

2.  **`requirements.txt`**:
    -   Add any additional Python libraries your service needs to function.

_You do not need to edit the `Dockerfile`._

### Step 4: Configure Docker Compose

Now, open the main `docker-compose.yml` file located in the **project root**.

Copy the entire YAML block below and paste it at the end of the `services:` section.

```yaml
# ------------------------------------------------------------------
# TEMPLATE FOR NEW SERVICE
# ------------------------------------------------------------------
# Instructions:
# 1. Replace ALL instances of `<your-service-name>`.
# 2. Replace `<your-api-route>` with your chosen URL path.
# 3. Replace `<your-unique-port>` with your chosen port number.
#
<your-service-name>:
  build:
    context: ./services/<your-service-name>
  container_name: <your-service-name>_service
  restart: unless-stopped
  networks:
    - localai_net
  environment:
    # This sets the port Gunicorn listens on INSIDE the container. MUST BE UNIQUE.
    - PORT=<your-unique-port>
    # Provide the URL for any other services this one needs to talk to.
    - CORE_SERVICE_URL=http://core-service:8000
  labels:
    - "traefik.enable=true"
    
    # --- Traefik Routing ---
    # The rule directs traffic from your domain + API path to this service.
    - "traefik.http.routers.<your-service-name>.rule=Host(`${DOMAIN_NAME}`) && PathPrefix(`/api/<your-api-route>`)"
    - "traefik.http.routers.<your-service-name>.priority=10"
    - "traefik.http.routers.<your-service-name>.entrypoints=https"
    - "traefik.http.routers.<your-service-name>.tls=true"
    
    # --- Traefik Service Definition ---
    # This tells Traefik which internal port to forward traffic to. MUST MATCH THE PORT ABOVE.
    - "traefik.http.services.<your-service-name>-svc.loadbalancer.server.port=<your-unique-port>"
```

After pasting the block, perform a find-and-replace on the placeholders (`<your-service-name>`, `<your-api-route>`, `<your-unique-port>`) with the values you decided on in Step 1.

### Step 5: Build and Deploy

From the project's **root directory**, run `docker-compose` with the `--build` flag to create the Docker image for your new service and start the container.

```bash
docker-compose up --build -d
```

### Step 6: Verify

Your new service is now running. You can check its logs with:

```bash
docker-compose logs -f <your-service-name>
```

The new API endpoint is accessible at `https://${DOMAIN_NAME}/api/<your-api-route>`.