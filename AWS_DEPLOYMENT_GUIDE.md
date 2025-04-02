# AWS Elastic Beanstalk Deployment Guide

This guide provides step-by-step instructions for deploying the Train Tracking application to AWS Elastic Beanstalk.

## Prerequisites

1. AWS Account with permissions to create:
   - Elastic Beanstalk environments
   - EC2 instances
   - S3 buckets
   - RDS databases (optional, for production)

2. AWS CLI and EB CLI installed and configured on your local machine:
   ```bash
   pip install awscli awsebcli
   aws configure  # Set up your AWS credentials
   ```

## Step 1: Prepare Your Application

1. Download your entire project from Replit
2. Make sure all necessary files are included:
   - Main application code (Python files)
   - `.ebextensions/` folder with configuration files
   - `.platform/` folder with platform hooks
   - `Procfile` specifying the web and worker processes
   - `aws_requirements.txt` for Python dependencies

## Step 2: Initialize Elastic Beanstalk Application

Navigate to your project directory in the terminal and run:

```bash
# Initialize the EB application
eb init -p python-3.8 scr-train-tracking

# When prompted:
# - Select your AWS region (typically closest to your users)
# - Create a new application
# - Select Python platform
# - Select latest Python version (3.8)
# - Set up SSH access if desired
```

## Step 3: Set Environment Variables

Before creating your environment, set up the required environment variables:

1. Create a file named `.env.yaml` in your project directory with the following content:

```yaml
option_settings:
  aws:elasticbeanstalk:application:environment:
    # Google Sheets Configuration
    GOOGLE_SHEETS_PROJECT_ID: "your-project-id"
    GOOGLE_SHEETS_PRIVATE_KEY_ID: "your-private-key-id"
    GOOGLE_SHEETS_PRIVATE_KEY: "your-private-key"
    GOOGLE_SHEETS_CLIENT_EMAIL: "your-client-email"
    GOOGLE_SHEETS_CLIENT_ID: "your-client-id"
    GOOGLE_SHEETS_CLIENT_X509_CERT_URL: "your-cert-url"
    GOOGLE_SHEETS_SPREADSHEET_ID: "your-spreadsheet-id"
    GOOGLE_SHEETS_SPREADSHEET_NAME: "your-spreadsheet-name"

    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN: "your-telegram-bot-token"
    TELEGRAM_CHAT_IDS: "your-telegram-chat-ids"

    # Twilio SMS Configuration
    TWILIO_ACCOUNT_SID: "your-twilio-account-sid"
    TWILIO_AUTH_TOKEN: "your-twilio-auth-token"
    TWILIO_PHONE_NUMBER: "your-twilio-phone-number"

    # SMS Country Configuration
    SMS_COUNTRY_API_KEY: "your-sms-country-api-key"
    SMS_COUNTRY_API_TOKEN: "your-sms-country-api-token"

    # General Notification Configuration
    NOTIFICATION_RECIPIENTS: "your-notification-recipients"

    # Database Configuration (Use RDS for production)
    DATABASE_URL: "postgresql://username:password@your-rds-endpoint:5432/database-name"
```

> **Important**: Replace all "your-*" values with your actual configuration values.

## Step 4: Create the Elastic Beanstalk Environment

Create your environment with:

```bash
# Create a new environment with the specified configuration
eb create train-tracking-prod --envvars-file .env.yaml
```

> **Note**: For production environments, you should consider using an RDS database by adding it through the EB console or using `.ebextensions` configuration.

## Step 5: Verify the Deployment

1. Once the environment is created, you can open the application with:
   ```bash
   eb open
   ```

2. Check the logs for any issues:
   ```bash
   eb logs
   ```

3. You can also SSH into the EC2 instance if needed:
   ```bash
   eb ssh
   ```

## Step 6: Update the Application

When you need to update your application:

1. Make changes to your code locally
2. Commit the changes to Git
3. Deploy the updated code:
   ```bash
   eb deploy
   ```

## Production Considerations

For a production deployment, consider these additional steps:

1. **Set up a custom domain name** through Route 53 or another DNS provider
2. **Configure HTTPS** with an SSL certificate from AWS Certificate Manager
3. **Set up auto-scaling** based on traffic patterns
4. **Use a dedicated RDS database** for better performance and reliability
5. **Set up CloudWatch Alarms** for monitoring and notifications
6. **Configure regular database backups**
7. **Implement a CI/CD pipeline** with AWS CodePipeline

## Troubleshooting

1. **Application not starting**:
   - Check logs: `eb logs`
   - SSH into the instance: `eb ssh` and check `/var/log/` for application logs

2. **Environment variables not loading**:
   - Verify they were set: `eb printenv`
   - Check if they are correctly referenced in the application

3. **Background service not running**:
   - SSH into the instance: `eb ssh`
   - Check the log file: `cat /var/log/background_notifier.log`
   - Manually run the service: `cd /var/app/current && python background_notifier.py`

4. **Database connection issues**:
   - Verify RDS security group allows connections from your EB environment
   - Check the connection string in environment variables
   - Consider using environment variables inside the Elastic Beanstalk console

## Important Notes

- This configuration is set up to deploy both the web application and the background notification service.
- The platform hooks ensure that your Streamlit secrets and configuration are properly set up.
- The daily reset cron job is configured to run at 01:00 UTC every day.
- Make sure to keep your AWS credentials and environment variables secure.
- Never commit `.env.yaml` or any file containing actual secrets to your Git repository.

For more information, refer to the [Elastic Beanstalk Documentation](https://docs.aws.amazon.com/elasticbeanstalk/).