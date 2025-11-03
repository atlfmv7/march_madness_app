# March Madness Madness - Production Deployment Guide

This guide walks you through deploying the March Madness app to production using Nginx and Gunicorn.

## Prerequisites

- Ubuntu/Debian Linux server
- Python 3.8+
- Nginx installed: `sudo apt install nginx`
- Gunicorn installed: `pip install gunicorn`
- Application repository cloned to `/home/user/march_madness_app`

## Deployment Steps

### 1. Create Required Directories

```bash
# Create log directories
sudo mkdir -p /var/log/march_madness
sudo mkdir -p /var/log/nginx
sudo mkdir -p /var/run/march_madness

# Set permissions (adjust user if not 'user')
sudo chown -R user:user /var/log/march_madness
sudo chown -R user:user /var/run/march_madness
```

### 2. Set Up Python Virtual Environment (if not already done)

```bash
cd /home/user/march_madness_app

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Initialize Database (if not already done)

```bash
# Make sure you're in the app directory with venv activated
python seed_data.py
```

### 4. Configure Systemd Service

```bash
# Copy service file to systemd directory
sudo cp march_madness.service /etc/systemd/system/

# Reload systemd to recognize new service
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable march_madness

# Start the service
sudo systemctl start march_madness

# Check service status
sudo systemctl status march_madness
```

### 5. Configure Nginx

```bash
# Copy Nginx configuration
sudo cp nginx_march_madness.conf /etc/nginx/sites-available/march_madness

# Create symbolic link to enable site
sudo ln -s /etc/nginx/sites-available/march_madness /etc/nginx/sites-enabled/

# Optional: Remove default Nginx site
sudo rm /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx

# Ensure Nginx starts on boot
sudo systemctl enable nginx
```

### 6. Configure Firewall (if using UFW)

```bash
# Allow Nginx through firewall
sudo ufw allow 'Nginx Full'

# Check firewall status
sudo ufw status
```

### 7. Verify Deployment

```bash
# Check Gunicorn service
sudo systemctl status march_madness

# Check Nginx service
sudo systemctl status nginx

# View application logs
sudo tail -f /var/log/march_madness/error.log
sudo tail -f /var/log/march_madness/access.log

# View Nginx logs
sudo tail -f /var/log/nginx/march_madness_error.log
sudo tail -f /var/log/nginx/march_madness_access.log
```

## Useful Commands

### Restart Services

```bash
# Restart application
sudo systemctl restart march_madness

# Reload Nginx (no downtime)
sudo systemctl reload nginx

# Restart Nginx (brief downtime)
sudo systemctl restart nginx
```

### Update Application

```bash
# Pull latest changes
cd /home/user/march_madness_app
git pull

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# Restart application
sudo systemctl restart march_madness
```

### View Logs

```bash
# Real-time application logs
sudo journalctl -u march_madness -f

# Last 100 lines of application logs
sudo journalctl -u march_madness -n 100

# Application error log
sudo tail -f /var/log/march_madness/error.log

# Nginx error log
sudo tail -f /var/log/nginx/march_madness_error.log
```

### Troubleshooting

```bash
# Check if Gunicorn is running
ps aux | grep gunicorn

# Check if port 8000 is listening
sudo netstat -tlnp | grep 8000

# Check Nginx configuration syntax
sudo nginx -t

# Check service status
sudo systemctl status march_madness
sudo systemctl status nginx
```

## Security Considerations

### 1. Change Default Secret Key

Update `app.py` with a strong secret key:

```python
app.config["SECRET_KEY"] = "your-very-long-random-secret-key-here"
```

Generate a secure key:
```bash
python -c 'import secrets; print(secrets.token_hex(32))'
```

### 2. Set Up SSL/HTTPS (Recommended)

Install Certbot for Let's Encrypt:

```bash
sudo apt install certbot python3-certbot-nginx

# Obtain SSL certificate (replace with your domain)
sudo certbot --nginx -d your-domain.com

# Certbot will automatically configure Nginx for HTTPS
```

### 3. Update Nginx Configuration

After getting SSL certificate, uncomment the HTTPS section in `nginx_march_madness.conf` and update with your domain.

### 4. Database Backups

Set up regular database backups:

```bash
# Create backup script
cat > /home/user/backup_db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/user/backups"
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d_%H%M%S)
cp /home/user/march_madness_app/march_madness.db $BACKUP_DIR/march_madness_$DATE.db
# Keep only last 7 days of backups
find $BACKUP_DIR -name "march_madness_*.db" -mtime +7 -delete
EOF

chmod +x /home/user/backup_db.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /home/user/backup_db.sh") | crontab -
```

## Environment Variables (Optional)

For production, consider using environment variables for sensitive settings:

```bash
# Create environment file
sudo nano /etc/march_madness.env

# Add variables
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///march_madness.db
```

Update `march_madness.service` to include:
```
EnvironmentFile=/etc/march_madness.env
```

## Monitoring

### Check Application Health

Visit your server's IP address or domain in a browser:
- `http://your-server-ip/` - Should show the bracket page
- `http://your-server-ip/table` - Should show the table view
- `http://192.168.150.x/admin` - Admin panel (only accessible from local network)

### Performance Monitoring

Consider setting up monitoring tools:
- **Logs**: Use `logrotate` to manage log files
- **Metrics**: Consider Prometheus + Grafana for monitoring
- **Uptime**: Use services like UptimeRobot or Pingdom

## Production Checklist

- [ ] Database initialized with seed data
- [ ] Gunicorn service running and enabled
- [ ] Nginx configured and running
- [ ] Firewall configured to allow HTTP/HTTPS
- [ ] SSL certificate installed (recommended)
- [ ] Database backups configured
- [ ] Logs rotating properly
- [ ] Application accessible from browser
- [ ] Admin panel restricted to local network
- [ ] Secret key changed from default

## Support

For issues, check:
1. Application logs: `/var/log/march_madness/error.log`
2. Nginx logs: `/var/log/nginx/march_madness_error.log`
3. Systemd logs: `sudo journalctl -u march_madness -n 100`
