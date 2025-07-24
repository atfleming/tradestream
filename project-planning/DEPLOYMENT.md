# 🚀 TradeStream Production Deployment Guide

## 📋 **Recommended Deployment Strategy**

### **🎯 Primary Recommendation: Cloud VPS with DigitalOcean**

**Why This Approach:**
- ✅ **24/7 Reliability**: Always-on trading without depending on your local machine
- ✅ **Cost Effective**: $12/month for production-ready 2GB RAM droplet
- ✅ **Simple Management**: Easy to setup, monitor, and maintain
- ✅ **Scalable**: Can upgrade resources as needed
- ✅ **Professional**: Proper production environment with systemd service

---

## 🛠️ **Step-by-Step Deployment Process**

### **Phase 1: Server Setup (15 minutes)**

#### **1.1 Create DigitalOcean Droplet**
```bash
# Option A: Using DigitalOcean Web Interface
# - Go to https://cloud.digitalocean.com/
# - Create Droplet → Ubuntu 22.04 LTS
# - Size: Basic $12/month (2GB RAM, 1 vCPU, 50GB SSD)
# - Region: Choose closest to your location
# - Authentication: SSH Key (recommended) or Password

# Option B: Using doctl CLI
doctl compute droplet create tradestream-prod \
  --image ubuntu-22-04-x64 \
  --size s-2vcpu-2gb \
  --region nyc1 \
  --ssh-keys your-ssh-key-id
```

#### **1.2 Initial Server Configuration**
```bash
# Connect to your droplet
ssh root@your-droplet-ip

# Update system packages
apt update && apt upgrade -y

# Install required packages
apt install -y python3 python3-pip git htop nano ufw fail2ban

# Configure firewall
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw enable

# Configure fail2ban for SSH protection
systemctl enable fail2ban
systemctl start fail2ban
```

### **Phase 2: TradeStream Installation (10 minutes)**

#### **2.1 Clone and Setup Application**
```bash
# Clone the repository
cd /opt
git clone https://github.com/atfleming/tradestream.git
cd tradestream

# Install Python dependencies
pip3 install -r requirements.txt

# Create configuration from template
cp config.yaml.example config.yaml
```

#### **2.2 Configure TradeStream**
```bash
# Edit configuration file
nano config.yaml

# Key settings to configure:
# - Discord bot token
# - Discord channel ID
# - Trading settings (paper_trading_enabled: true for testing)
# - Email notifications (optional)
# - Risk management limits
```

#### **2.3 Create Application User (Security Best Practice)**
```bash
# Create dedicated user for TradeStream
useradd -r -s /bin/false -d /opt/tradestream tradestream
chown -R tradestream:tradestream /opt/tradestream

# Create data directories
mkdir -p /opt/tradestream/{data,logs,backups}
chown -R tradestream:tradestream /opt/tradestream/{data,logs,backups}
```

### **Phase 3: Production Service Setup (10 minutes)**

#### **3.1 Create Systemd Service**
```bash
# Create service file
nano /etc/systemd/system/tradestream.service
```

**Service Configuration:**
```ini
[Unit]
Description=TradeStream Automated Trading Bot
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=tradestream
Group=tradestream
WorkingDirectory=/opt/tradestream
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=tradestream

# Environment variables
Environment=PYTHONPATH=/opt/tradestream/src
Environment=PYTHONUNBUFFERED=1

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/tradestream/data /opt/tradestream/logs /opt/tradestream/backups

[Install]
WantedBy=multi-user.target
```

#### **3.2 Enable and Start Service**
```bash
# Reload systemd and enable service
systemctl daemon-reload
systemctl enable tradestream
systemctl start tradestream

# Check service status
systemctl status tradestream

# View logs
journalctl -u tradestream -f
```

### **Phase 4: Monitoring and Maintenance (5 minutes)**

#### **4.1 Setup Log Rotation**
```bash
# Create logrotate configuration
nano /etc/logrotate.d/tradestream
```

```
/opt/tradestream/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 tradestream tradestream
    postrotate
        systemctl reload tradestream
    endscript
}
```

#### **4.2 Setup Automated Backups**
```bash
# Create backup script
nano /opt/tradestream/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/opt/tradestream/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup
tar -czf "$BACKUP_DIR/tradestream_backup_$DATE.tar.gz" \
    /opt/tradestream/data \
    /opt/tradestream/config.yaml \
    /opt/tradestream/logs

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "tradestream_backup_*.tar.gz" -mtime +7 -delete

echo "Backup completed: tradestream_backup_$DATE.tar.gz"
```

```bash
# Make executable and setup cron
chmod +x /opt/tradestream/backup.sh
crontab -e

# Add daily backup at 2 AM
0 2 * * * /opt/tradestream/backup.sh >> /var/log/tradestream-backup.log 2>&1
```

---

## 🔧 **Management Commands**

### **Service Management**
```bash
# Start service
systemctl start tradestream

# Stop service
systemctl stop tradestream

# Restart service
systemctl restart tradestream

# Check status
systemctl status tradestream

# View logs (live)
journalctl -u tradestream -f

# View recent logs
journalctl -u tradestream --since "1 hour ago"
```

### **Application Updates**
```bash
# Stop service
systemctl stop tradestream

# Update code
cd /opt/tradestream
git pull origin main

# Install any new dependencies
pip3 install -r requirements.txt

# Start service
systemctl start tradestream

# Verify deployment
systemctl status tradestream
```

### **Configuration Changes**
```bash
# Edit configuration
nano /opt/tradestream/config.yaml

# Restart to apply changes
systemctl restart tradestream
```

---

## 📊 **Monitoring and Alerts**

### **Health Checks**
```bash
# Check if service is running
systemctl is-active tradestream

# Check resource usage
htop

# Check disk space
df -h

# Check memory usage
free -h

# View application logs
tail -f /opt/tradestream/logs/tradestream.log
```

### **Performance Monitoring**
```bash
# Monitor system resources
watch -n 5 'systemctl status tradestream && free -h && df -h'

# Check network connections
netstat -tulpn | grep python

# Monitor log file sizes
du -sh /opt/tradestream/logs/*
```

---

## 🔒 **Security Best Practices**

### **Server Security**
- ✅ **SSH Key Authentication**: Disable password login
- ✅ **Firewall**: UFW configured with minimal open ports
- ✅ **Fail2ban**: Protection against brute force attacks
- ✅ **Regular Updates**: Keep system packages updated
- ✅ **Dedicated User**: TradeStream runs as non-root user

### **Application Security**
- ✅ **Configuration Protection**: Secure file permissions on config.yaml
- ✅ **Environment Variables**: Sensitive data in environment variables
- ✅ **Log Security**: No sensitive data in logs
- ✅ **Network Security**: Minimal network exposure

### **Maintenance Security**
```bash
# Regular security updates
apt update && apt upgrade -y

# Check for failed login attempts
journalctl -u ssh --since "24 hours ago" | grep "Failed"

# Monitor system logs
tail -f /var/log/auth.log
```

---

## 💰 **Cost Breakdown**

### **Monthly Costs**
- **DigitalOcean Droplet**: $12/month (2GB RAM, 50GB SSD)
- **Backup Storage**: ~$1/month (if using external backup)
- **Domain Name**: ~$1/month (optional, for monitoring dashboard)
- **Total**: ~$13-15/month

### **Annual Costs**
- **Server**: $144/year
- **Backup**: $12/year
- **Domain**: $12/year
- **Total**: ~$168/year

---

## 🚨 **Troubleshooting**

### **Common Issues**

#### **Service Won't Start**
```bash
# Check service status
systemctl status tradestream

# Check logs for errors
journalctl -u tradestream --since "10 minutes ago"

# Check configuration syntax
python3 -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Check file permissions
ls -la /opt/tradestream/config.yaml
```

#### **High Memory Usage**
```bash
# Check memory usage
free -h
ps aux | grep python

# Restart service to clear memory
systemctl restart tradestream
```

#### **Disk Space Issues**
```bash
# Check disk usage
df -h
du -sh /opt/tradestream/*

# Clean old logs
find /opt/tradestream/logs -name "*.log" -mtime +30 -delete

# Clean old backups
find /opt/tradestream/backups -name "*.tar.gz" -mtime +7 -delete
```

---

## 📈 **Scaling and Optimization**

### **Performance Optimization**
- **Upgrade Droplet**: Scale to 4GB RAM if needed
- **SSD Storage**: Already included in recommended setup
- **Database Optimization**: SQLite is sufficient for most use cases
- **Log Management**: Implement log rotation and compression

### **High Availability Options**
- **Load Balancer**: Multiple droplets behind load balancer
- **Database Replication**: External database with replication
- **Monitoring**: External monitoring service (Datadog, New Relic)
- **Backup Strategy**: Multi-region backup storage

---

## ✅ **Deployment Checklist**

### **Pre-Deployment**
- [ ] DigitalOcean account created
- [ ] SSH key generated and added
- [ ] Discord bot token obtained
- [ ] Discord channel ID identified
- [ ] Email credentials ready (if using notifications)

### **Deployment**
- [ ] Droplet created and configured
- [ ] TradeStream cloned and installed
- [ ] Configuration file updated
- [ ] Systemd service created and enabled
- [ ] Service started and verified
- [ ] Logs checked for errors

### **Post-Deployment**
- [ ] Backup script configured
- [ ] Log rotation setup
- [ ] Monitoring configured
- [ ] Security hardening completed
- [ ] Documentation updated
- [ ] Emergency procedures documented

---

## 🎯 **Next Steps After Deployment**

1. **Testing Phase**: Run in paper trading mode for 1-2 weeks
2. **Performance Monitoring**: Monitor system resources and trading performance
3. **Optimization**: Adjust configuration based on real-world performance
4. **Live Trading**: Switch to live trading after thorough testing
5. **Scaling**: Upgrade resources as trading volume increases

---

## 📞 **Support and Maintenance**

### **Regular Maintenance Schedule**
- **Daily**: Check service status and logs
- **Weekly**: Review trading performance and system resources
- **Monthly**: Update system packages and review security
- **Quarterly**: Full system backup and disaster recovery test

### **Emergency Procedures**
- **Service Down**: Restart service, check logs, verify configuration
- **High Resource Usage**: Monitor processes, restart if needed, consider upgrade
- **Security Incident**: Review logs, update passwords, check for unauthorized access
- **Data Loss**: Restore from backup, verify data integrity

---

*This deployment guide provides a production-ready setup for TradeStream with proper security, monitoring, and maintenance procedures. Follow the steps carefully and test thoroughly before deploying to live trading.*
