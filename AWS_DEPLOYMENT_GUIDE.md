# Train Tracking Application - AWS Elastic Beanstalk Deployment Guide

This document provides comprehensive instructions for deploying the SCR Vijayawada Division Train Tracking application on AWS Elastic Beanstalk.

## Prerequisites

1. **AWS Account**: Active AWS account with appropriate permissions
2. **AWS CLI**: Install from [https://aws.amazon.com/cli/](https://aws.amazon.com/cli/)
3. **EB CLI**: Install with `pip install awsebcli`
4. **Your Application Code**: Complete codebase of the train tracking application

## Step 1: Prepare Your Application

### File Structure

Ensure your application has the following structure:

```
train-tracking-app/
├── main.py                         # Main Streamlit application
├── pages/                          # Streamlit pages
├── notifications/                  # Notification modules
├── background_notifier.py          # Background notification service
├── reset_trains.py                 # Daily reset script
├── requirements.txt                # Python dependencies
├── Procfile                        # Process file for Elastic Beanstalk
├── .ebextensions/                  # EB configuration files
│   ├── 01_packages.config          # Package installations
│   ├── 02_python.config            # Python settings
│   └── 03_cronjob.config           # Cron job for daily reset
└── .platform/                      # Platform hooks and configurations
    ├── nginx/
    │   └── conf.d/
    │       └── proxy.conf          # Nginx configuration
    └── hooks/
        └── predeploy/
            ├── 01_env.config       # Environment setup
            └── 02_start_service.config  # Background service starter
```

### Required Configuration Files

1. **requirements.txt**:

```
streamlit==1.31.0
pandas==2.0.3
folium==0.14.0
psutil==5.9.5
python-telegram-bot==13.15
numpy==1.24.3
sqlalchemy==2.0.19
psycopg2-binary==2.9.6
cairosvg==2.7.0
plotly==5.15.0
twilio==8.5.0
gspread==5.10.0
google-auth==2.22.0
oauth2client==4.1.3
trafilatura==1.6.1
openpyxl==3.1.2
python-dateutil==2.8.2
toml==0.10.2
```

2. **Procfile**:

```
web: streamlit run --server.port=$PORT --server.address=0.0.0.0 main.py
```

3. **.ebextensions/01_packages.config**:

```yaml
packages:
  yum:
    git: []
    postgresql-devel: []
    gcc: []
    python3-devel: []
```

4. **.ebextensions/02_python.config**:

```yaml
option_settings:
  aws:elasticbeanstalk:container:python:
    WSGIPath: main.py
  aws:elasticbeanstalk:application:environment:
    PYTHONPATH: "/var/app/current:$PYTHONPATH"
```

5. **.ebextensions/03_cronjob.config**:

```yaml
files:
  "/etc/cron.d/reset_trains":
    mode: "000644"
    owner: root
    group: root
    content: |
      0 1 * * * root python /var/app/current/reset_trains.py >> /var/log/reset_trains.log 2>&1

commands:
  01_remove_old_cron:
    command: "rm -f /etc/cron.d/reset_trains.bak"
  02_start_crond:
    command: "service crond restart || service cron restart"
```

6. **.platform/nginx/conf.d/proxy.conf**:

```nginx
server {
    listen 80;
    
    gzip on;
    gzip_comp_level 4;
    gzip_types text/plain text/css application/json application/javascript application/x-javascript text/xml application/xml application/xml+rss text/javascript;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 90;
    }
}
```

7. **.platform/hooks/predeploy/01_env.config**:

```bash
#!/bin/bash
# Set environment variables
echo 'export PORT=5000' >> /opt/elasticbeanstalk/deployment/env
echo 'export PYTHONUNBUFFERED=1' >> /opt/elasticbeanstalk/deployment/env
```

8. **.platform/hooks/predeploy/02_start_service.config**:

```bash
#!/bin/bash
# Start the background notification service
cd /var/app/staging
mkdir -p temp
chmod +x background_notifier.py
nohup python background_notifier.py > /var/log/background_notifier.log 2>&1 &
```

Make the hook scripts executable:

```bash
chmod +x .platform/hooks/predeploy/01_env.config
chmod +x .platform/hooks/predeploy/02_start_service.config
```

## Step 2: Set Up RDS PostgreSQL Database (Optional)

If your application uses PostgreSQL:

1. **Create an RDS instance** through the AWS Console:
   - Navigate to RDS in AWS Console
   - Click "Create database"
   - Select PostgreSQL
   - Choose appropriate settings for size and availability
   - Set up security groups to allow access from your Elastic Beanstalk environment

2. **Add database configuration** in `.ebextensions/04_database.config`:

```yaml
Resources:
  AWSEBSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Security group for RDS access
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 5432
          ToPort: 5432
          SourceSecurityGroupId: 
            Fn::GetAtt: [AWSEBSecurityGroup, GroupId]

option_settings:
  aws:elasticbeanstalk:application:environment:
    DATABASE_URL: "postgresql://username:password@your-rds-endpoint:5432/database_name"
```

## Step 3: Create and Deploy the Elastic Beanstalk Application

1. **Initialize the EB application**:

```bash
# Navigate to your project directory
cd train-tracking-app

# Initialize Elastic Beanstalk application
eb init -p python-3.8 scr-train-tracking

# When prompted:
# - Select your region
# - Create new application if prompted
# - Select Python platform
# - Choose Python 3.8
# - Set up SSH if needed
```

2. **Create an environment and deploy**:

```bash
# Create a production environment
eb create train-tracking-prod --instance-type t2.small --single

# This will:
# - Create a new environment
# - Deploy your application
# - Set up the necessary resources
```

3. **Configure environment variables** through the AWS Console:
   - Navigate to your Elastic Beanstalk environment
   - Go to "Configuration" → "Software" → "Environment properties"
   - Add all required secret keys:
     - `TELEGRAM_BOT_TOKEN`
     - `TELEGRAM_CHAT_IDS` 
     - `TWILIO_ACCOUNT_SID`
     - `TWILIO_AUTH_TOKEN`
     - `TWILIO_PHONE_NUMBER`
     - `SMS_COUNTRY_API_KEY`
     - `SMS_COUNTRY_API_TOKEN`
     - `NOTIFICATION_RECIPIENTS`

4. **Deploy updates** after making changes:

```bash
# After updating your application code
eb deploy
```

## Step 4: Monitoring and Maintenance

### Accessing Logs

1. **View application logs** from the EB console:
   - Navigate to your environment
   - Go to "Logs" → "Request Logs" → "Full Logs"

2. **SSH into your instance** for troubleshooting:

```bash
eb ssh
```

3. **Check specific logs**:

```bash
# Application logs
sudo cat /var/log/web.stdout.log

# Background service logs
sudo cat /var/log/background_notifier.log

# Reset script logs
sudo cat /var/log/reset_trains.log
```

### Scaling Configuration

To configure auto-scaling, create `.ebextensions/05_scaling.config`:

```yaml
option_settings:
  aws:autoscaling:asg:
    MinSize: '1'
    MaxSize: '3'
  aws:autoscaling:trigger:
    BreachDuration: 5
    UpperThreshold: 80
    LowerThreshold: 40
    MeasureName: CPUUtilization
    Unit: Percent
    UpperBreachScaleIncrement: 1
    LowerBreachScaleIncrement: -1
```

### Health Checks

To customize health checks, create `.ebextensions/06_health.config`:

```yaml
option_settings:
  aws:elasticbeanstalk:application:
    Application Healthcheck URL: /
  aws:elasticbeanstalk:environment:health:
    SystemType: enhanced
    HealthCheckSuccessThreshold: Warning
```

## Step 5: Production Hardening

For a production environment, add these additional configurations:

1. **HTTPS Configuration** in `.ebextensions/07_https.config`:

```yaml
Resources:
  sslSecurityGroupIngress:
    Type: AWS::EC2::SecurityGroupIngress
    Properties:
      GroupId: {"Fn::GetAtt" : ["AWSEBSecurityGroup", "GroupId"]}
      IpProtocol: tcp
      ToPort: 443
      FromPort: 443
      CidrIp: 0.0.0.0/0

option_settings:
  aws:elasticbeanstalk:environment:
    LoadBalancerType: application
  aws:elbv2:listener:443:
    Protocol: HTTPS
    SSLCertificateArns: arn:aws:acm:region:account-id:certificate/certificate-id
```

2. **Session Stickiness** for consistent user experience:

```yaml
option_settings:
  aws:elasticbeanstalk:environment:process:default:
    StickinessEnabled: true
    StickinessLBCookieDuration: '86400'
```

## Step 6: Clean Up Resources

When you no longer need the environment:

```bash
# Terminate the environment
eb terminate train-tracking-prod
```

**Important**: This deletes the Elastic Beanstalk environment but not:
- The EB application itself
- RDS databases
- S3 buckets created during deployment

To fully clean up, manually delete these resources through the AWS Console.

## Troubleshooting

### Common Issues and Solutions

1. **Application not starting**:
   - Check `/var/log/web.stdout.log` for errors
   - Verify environment variables are set correctly
   - Make sure the Procfile is properly configured

2. **Database connection issues**:
   - Verify security groups allow traffic from EB to RDS
   - Check database credentials in environment variables
   - Ensure the database has been initialized with the required tables

3. **Background service not running**:
   - Check `/var/log/background_notifier.log` for errors
   - Verify the predeploy hook is executable
   - Make sure all required environment variables are accessible to the service

4. **Daily reset not working**:
   - Check `/var/log/reset_trains.log` for errors
   - Verify cron is running with `systemctl status crond`
   - Ensure the cron job configuration is correct

## Security Considerations

1. **Never store secrets in code** - Always use environment variables
2. **Restrict security groups** to only necessary traffic
3. **Use IAM roles** for EC2 instances instead of hardcoded credentials
4. **Enable HTTPS** for all production traffic
5. **Regularly update dependencies** to patch security vulnerabilities

---

For additional assistance, refer to the [AWS Elastic Beanstalk Documentation](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/Welcome.html).