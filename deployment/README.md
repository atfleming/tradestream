# 🚀 TradeStream Deployment

This folder contains all deployment-related files for TradeStream automated trading system.

## 📁 Contents

### 🎯 Demo & Testing
- **`demo_tradestream.py`** - Demo script for testing TradeStream functionality
  - Paper trading simulation
  - Live trading connectivity tests
  - System health validation

### 🐳 Docker Deployment
- **`Dockerfile`** - Container image definition for TradeStream
- **`docker-compose.yml`** - Multi-container orchestration with dependencies

### ☸️ Kubernetes Deployment
- **`k8s-deployment.yaml`** - Kubernetes deployment configuration
  - Pod specifications
  - Service definitions
  - ConfigMap and Secret management

## 🚀 Quick Start

### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f tradestream
```

### Kubernetes Deployment
```bash
# Apply Kubernetes configuration
kubectl apply -f k8s-deployment.yaml

# Check deployment status
kubectl get pods -l app=tradestream
```

### Demo Testing
```bash
# Run demo script
python deployment/demo_tradestream.py

# Test with specific configuration
python deployment/demo_tradestream.py --config config.yaml --mode paper
```

## 📋 Prerequisites

- **Docker**: Version 20.0+ for containerized deployment
- **Kubernetes**: Version 1.20+ for K8s deployment
- **Python 3.8+**: For demo script execution
- **TopStepX Account**: For live trading functionality

## 🔧 Configuration

All deployment methods use the same configuration files:
- `config.yaml` - Main configuration
- `.env` - Environment variables and secrets

Refer to the main [README.md](../README.md) for detailed configuration instructions.

## 🛡️ Security Notes

- Never include credentials in deployment files
- Use Kubernetes Secrets or Docker Secrets for sensitive data
- Ensure proper network policies and access controls
- Regular security updates for base images

## 📊 Monitoring

Each deployment method includes:
- Health check endpoints
- Logging configuration
- Performance metrics
- Error reporting

For detailed monitoring setup, see [docs/DEPLOYMENT.md](../project-planning/DEPLOYMENT.md).
