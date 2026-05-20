# Docker Guide

## Essential Commands
```bash
docker build -t myapp:latest .
docker run -d -p 8080:80 --name myapp myapp:latest
docker exec -it myapp /bin/bash
docker logs -f myapp
docker compose up -d
docker compose down -v
docker system prune -af
```

## Dockerfile Best Practices
```dockerfile
FROM python:3.11-slim AS base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

## Multi-stage Builds
```dockerfile
FROM node:18 AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
```

## Common Issues
- "No space left" → `docker system prune`
- Container exits immediately → Check `docker logs`
- Port already in use → `lsof -i :8080`
- Permission denied → Add `--user $(id -u):$(id -g)`
