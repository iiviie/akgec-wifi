# AKGEC WiFi RADIUS Authentication Setup

This guide documents the complete process of setting up a FreeRADIUS server on Arch Linux to authenticate users against a Django SQLite database for WiFi access.

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Database Setup](#database-setup)
- [FreeRADIUS Configuration](#freeradius-configuration)
- [Authentication Script](#authentication-script)
- [Testing](#testing)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)

## Overview

This project integrates Django user authentication with FreeRADIUS to provide WiFi access control. Users stored in a Django SQLite database can authenticate through RADIUS protocol for WiFi access.

### Architecture
- **Django Application**: Manages user accounts and web interface
- **SQLite Database**: Stores user credentials with MD5 hashed passwords
- **FreeRADIUS Server**: Handles RADIUS authentication requests
- **Python Script**: Bridges FreeRADIUS and Django database
- **WiFi Access Points**: Forward authentication requests to RADIUS server

## Prerequisites

- Arch Linux system
- Python 3.x installed
- Django project with user authentication
- Root/sudo access

## Installation

### 1. Update System and Install FreeRADIUS

```bash
# Update system packages
sudo pacman -Syu

# Install FreeRADIUS and Python
sudo pacman -S freeradius python

# Stop the service initially for configuration
sudo systemctl stop radiusd
```

### 2. Create Directory Structure

```bash
# Create scripts directory for custom authentication
sudo mkdir -p /etc/raddb/scripts

# Create project directory for Django database
sudo mkdir -p /etc/raddb/scripts/AKGECWifi
```

## Database Setup

### 1. Setup Django Virtual Environment

```bash
# Navigate to your Django project directory
cd /path/to/akgec-wifi

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install Django dependencies
pip install -r requirements.txt
```

### 2. Create Django Database and Users

```bash
# Run Django migrations to create database
python manage.py migrate

# Open Django shell to create test users
python manage.py shell
```

In Django shell:
```python
from captive_portal.models import StudentModel
import hashlib

# Create test users (Django automatically hashes passwords with MD5)
user1 = StudentModel(
    username='testuser',
    password='hello',  # Will be hashed to MD5 automatically
    email='test@akgec.ac.in'
)
user1.save()

user2 = StudentModel(
    username='admin',
    password='123456',  # Will be hashed to MD5 automatically
    email='admin@akgec.ac.in'
)
user2.save()

# Verify users were created
for user in StudentModel.objects.all():
    print(f"Username: {user.username}, Email: {user.email}")

exit()
```

### 3. Copy Database to FreeRADIUS Directory

```bash
# Copy Django SQLite database to FreeRADIUS directory
sudo cp db.sqlite3 /etc/raddb/scripts/AKGECWifi/

# Set proper ownership and permissions
sudo chown radiusd:radiusd /etc/raddb/scripts/AKGECWifi/db.sqlite3
sudo chmod 644 /etc/raddb/scripts/AKGECWifi/db.sqlite3

# Verify database contents
sqlite3 /etc/raddb/scripts/AKGECWifi/db.sqlite3 "SELECT username, password FROM captive_portal_studentmodel;"
```

## FreeRADIUS Configuration

### 1. Create Authentication Script

```bash
# Create the Python authentication script
sudo tee /etc/raddb/scripts/auth.py > /dev/null << 'EOF'
#!/usr/bin/env python3
import hashlib
import sqlite3
import sys
import re

# Database path
db_path = "/etc/raddb/scripts/AKGECWifi/db.sqlite3"

def sanitize_input(username, password):
    """Validate username and sanitize password"""
    if not re.match("^[A-Za-z0-9_]{1,50}$", username):
        return None, None
    
    password = re.sub(r'[^A-Za-z0-9!@#$%^&*()_+={}\[\]:;"\'<>,.?/-]', '', password.strip())
    return username, password

def authenticate_user(username, password):
    """Authenticate user against database"""
    try:
        hashed_input_password = hashlib.md5(password.encode()).hexdigest()
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()
        cursor.execute(
            "SELECT password FROM captive_portal_studentmodel WHERE username = ?",
            (username,),
        )
        result = cursor.fetchone()
        connection.close()
        
        if result and hashed_input_password == result[0]:
            # Authentication successful - set cleartext password for PAP
            print(f"Cleartext-Password := \"{password}\"")
            print(f"Reply-Message := \"Welcome {username}\"")
            return 0
        else:
            # Authentication failed
            return 1
            
    except Exception:
        return 1

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    
    username, password = sanitize_input(username, password)
    
    if not username or not password:
        sys.exit(1)
    
    exit_code = authenticate_user(username, password)
    sys.exit(exit_code)
EOF

# Set proper permissions
sudo chmod +x /etc/raddb/scripts/auth.py
sudo chown radiusd:radiusd /etc/raddb/scripts/auth.py
```

### 2. Create Custom Module Configuration

```bash
# Create the AKGEC authentication module
sudo tee /etc/raddb/mods-available/akgec_auth > /dev/null << 'EOF'
exec akgec_auth {
    wait = yes
    program = "/usr/bin/python3 /etc/raddb/scripts/auth.py '%{User-Name}' '%{User-Password}'"
    input_pairs = request
    output_pairs = control
    shell_escape = yes
    timeout = 10
}
EOF

# Enable the module
sudo ln -s /etc/raddb/mods-available/akgec_auth /etc/raddb/mods-enabled/akgec_auth
```

### 3. Disable EAP Module (Not Needed for Basic Auth)

```bash
# Remove EAP module as it's not needed for username/password auth
sudo rm -f /etc/raddb/mods-enabled/eap

# Remove inner-tunnel site (used for EAP)
sudo rm -f /etc/raddb/sites-enabled/inner-tunnel
```

### 4. Configure RADIUS Clients

```bash
# Edit clients configuration
sudo nano /etc/raddb/clients.conf
```

Add to the end of the file:
```
# AKGEC WiFi Client Configuration
client akgec-wifi {
    ipaddr = 192.168.1.0/24
    secret = your_strong_shared_secret_here
    shortname = akgec-wifi
    nas_type = other
}
```

### 5. Configure Site Authorization

```bash
# Edit the default site configuration
sudo nano /etc/raddb/sites-enabled/default
```

Ensure the `authorize` section includes:
```
authorize {
    preprocess
    chap
    mschap
    digest
    suffix
    files
    
    # Custom AKGEC authentication
    akgec_auth
    
    expiration
    logintime
    pap
}
```

And the `authenticate` section includes:
```
authenticate {
    Auth-Type PAP {
        pap
    }
    
    Auth-Type CHAP {
        chap
    }
    
    Auth-Type MS-CHAP {
        mschap
    }
}
```

### 6. Setup Log Permissions

```bash
# Create log file with proper permissions
sudo touch /tmp/authentication.log
sudo chown radiusd:radiusd /tmp/authentication.log
sudo chmod 644 /tmp/authentication.log
```

## Testing

### 1. Test Configuration Syntax

```bash
# Verify FreeRADIUS configuration is valid
sudo radiusd -CX
```

Expected output: "Configuration appears to be OK"

### 2. Test Authentication Script Manually

```bash
# Test the Python script directly
sudo -u radiusd python3 /etc/raddb/scripts/auth.py testuser hello
```

Expected output:
```
Cleartext-Password := "hello"
Reply-Message := "Welcome testuser"
```

### 3. Test FreeRADIUS in Debug Mode

```bash
# Start FreeRADIUS in debug mode
sudo radiusd -X
```

### 4. Test RADIUS Authentication

In another terminal:
```bash
# Test successful authentication
radtest testuser hello localhost 1812 testing123

# Test with admin user
radtest admin 123456 localhost 1812 testing123

# Test failed authentication (wrong password)
radtest testuser wrongpassword localhost 1812 testing123

# Test non-existent user
radtest nonexistentuser somepassword localhost 1812 testing123
```

### Expected Results

**Successful Authentication:**
```
Sent Access-Request Id 217 from 0.0.0.0:59863 to 127.0.0.1:1812 length 78
        User-Name = "testuser"
        User-Password = "hello"
        ...
Received Access-Accept Id 217 from 127.0.0.1:1812 to 127.0.0.1:59863 length 38
```

**Failed Authentication:**
```
Sent Access-Request Id 218 from 0.0.0.0:59864 to 127.0.0.1:1812 length 78
        User-Name = "testuser"
        User-Password = "wrongpassword"
        ...
Received Access-Reject Id 218 from 127.0.0.1:1812 to 127.0.0.1:59864 length 38
```

## Production Deployment

### 1. Start and Enable RADIUS Service

```bash
# Stop debug mode (Ctrl+C)

# Start the RADIUS service
sudo systemctl start radiusd

# Enable service to start on boot
sudo systemctl enable radiusd

# Check service status
sudo systemctl status radiusd
```

### 2. Configure WiFi Access Points

Configure your WiFi access points with:
- **RADIUS Server IP**: Your server's IP address
- **RADIUS Port**: 1812 (authentication)
- **Shared Secret**: The secret configured in clients.conf
- **Authentication Method**: PAP/CHAP

### 3. Monitor Logs

```bash
# Monitor authentication attempts
tail -f /tmp/authentication.log

# Monitor system logs
sudo journalctl -u radiusd -f
```

### 4. Database Synchronization

To keep the RADIUS database synchronized with Django:

```bash
# Create a script to sync database regularly
sudo tee /etc/raddb/scripts/sync_db.sh > /dev/null << 'EOF'
#!/bin/bash
# Sync Django database to RADIUS directory
cp /path/to/your/django/project/db.sqlite3 /etc/raddb/scripts/AKGECWifi/
chown radiusd:radiusd /etc/raddb/scripts/AKGECWifi/db.sqlite3
chmod 644 /etc/raddb/scripts/AKGECWifi/db.sqlite3
EOF

sudo chmod +x /etc/raddb/scripts/sync_db.sh

# Add to crontab for automatic sync (optional)
# sudo crontab -e
# Add: */5 * * * * /etc/raddb/scripts/sync_db.sh
```

## Troubleshooting

### Common Issues

1. **Permission Denied Errors**
   ```bash
   sudo chown -R radiusd:radiusd /etc/raddb/scripts/
   sudo chmod +x /etc/raddb/scripts/auth.py
   ```

2. **Database Connection Errors**
   ```bash
   # Check database exists and is readable
   sudo -u radiusd sqlite3 /etc/raddb/scripts/AKGECWifi/db.sqlite3 ".tables"
   ```

3. **Authentication Always Fails**
   ```bash
   # Check password hashes match
   python -c "import hashlib; print(hashlib.md5('hello'.encode()).hexdigest())"
   ```

4. **Module Not Found Errors**
   ```bash
   # Verify module is enabled
   ls -la /etc/raddb/mods-enabled/akgec_auth
   ```

### Debug Commands

```bash
# Test configuration syntax
sudo radiusd -CX

# Run in debug mode
sudo radiusd -X

# Test script manually
sudo -u radiusd python3 /etc/raddb/scripts/auth.py testuser hello

# Check database contents
sqlite3 /etc/raddb/scripts/AKGECWifi/db.sqlite3 "SELECT * FROM captive_portal_studentmodel;"

# Monitor logs
tail -f /tmp/authentication.log
sudo journalctl -u radiusd -n 50
```

## Security Considerations

1. **Change Default Secrets**: Replace `testing123` with strong shared secrets
2. **Firewall Rules**: Restrict access to RADIUS ports (1812/1813)
3. **Database Security**: Secure the SQLite database file
4. **Regular Updates**: Keep FreeRADIUS and system packages updated
5. **Log Monitoring**: Monitor authentication logs for suspicious activity

## Adding New Users

Users can be added through the Django admin interface or programmatically:

```python
# In Django shell
from captive_portal.models import StudentModel

user = StudentModel(
    username='newuser',
    password='password123',  # Will be auto-hashed
    email='newuser@akgec.ac.in'
)
user.save()
```

After adding users, sync the database:
```bash
sudo /etc/raddb/scripts/sync_db.sh
```

## Commands Reference

| Command | Purpose |
|---------|---------|
| `sudo radiusd -CX` | Test configuration syntax |
| `sudo radiusd -X` | Run in debug mode |
| `radtest user pass server port secret` | Test RADIUS authentication |
| `sudo systemctl status radiusd` | Check service status |
| `tail -f /tmp/authentication.log` | Monitor auth logs |
| `sqlite3 db.sqlite3 "SELECT * FROM table;"` | Query database |

---

## Project Structure

```
/etc/raddb/
├── scripts/
│   ├── auth.py                    # Authentication script
│   ├── sync_db.sh                 # Database sync script
│   └── AKGECWifi/
│       └── db.sqlite3             # Django database copy
├── mods-enabled/
│   └── akgec_auth -> ../mods-available/akgec_auth
├── mods-available/
│   └── akgec_auth                 # Custom module config
├── sites-enabled/
│   └── default                    # Main site configuration
└── clients.conf                   # RADIUS client configuration
```

This setup provides a robust, scalable WiFi authentication system integrated with your Django application.