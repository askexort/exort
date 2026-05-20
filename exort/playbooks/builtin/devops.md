# DevOps Quick Reference

## Docker
```bash
docker build -t app:latest .
docker run -d -p 8080:8080 --name app app:latest
docker logs -f app
docker exec -it app /bin/sh
```

## Common Patterns
- Multi-stage builds for smaller images
- Health checks in Dockerfile
- Non-root user in container
- .dockerignore for faster builds

## CI/CD
- Test on every push
- Build and tag on merge to main
- Deploy on tags/releases
- Rollback strategy

## Monitoring
- Uptime checks
- Error rate alerts
- Latency percentiles
- Resource usage (CPU, memory, disk)
- Log aggregation

## Incident Response
1. Acknowledge the issue
2. Assess impact
3. Mitigate (rollback, scale, restart)
4. Root cause analysis
5. Post-mortem and action items
