# SendGrid Configuration Guide

This guide explains how to set up SendGrid for user verification emails in the Binghamton Housing Portal.

## Step 1: Create a SendGrid Account

If you haven't already, create an account at [SendGrid](https://sendgrid.com/).

## Step 2: Verify Your Sender Identity

1. In your SendGrid dashboard, go to **Settings** > **Sender Authentication**
2. Click on **Single Sender Verification**
3. Fill in the details as shown in your account:
   - **From Name**: Binghamton Housing Portal
   - **From Email**: spencermines1@gmail.com
   - **Reply To**: spencermines1@gmail.com
   - **Company Address**: 4400 Vestal Parkway E, Binghamton, NY 13850 US
   - **City**: Binghamton
   - **State**: New York
   - **Zip Code**: 13850
   - **Country**: United States
   - **Nickname**: Binghamton Housing

4. Click **Save** and follow the verification email sent to spencermines1@gmail.com

## Step 3: Create an API Key

1. Go to **Settings** > **API Keys** in the SendGrid dashboard
2. Click **Create API Key**
3. Name it something like "Binghamton Housing Portal API Key"
4. Choose "Full Access" or "Restricted Access" with Mail Send permissions
5. Copy the generated API key (you'll only see it once)

## Step 4: Configure Your Local Environment

Create a `.env` file in your project root with the following values:

```
# SendGrid configuration
SENDGRID_API_KEY=your-api-key-here
SENDGRID_FROM_EMAIL=spencermines1@gmail.com
SENDGRID_FROM_NAME=Binghamton Housing Portal
```

Replace `your-api-key-here` with the API key you generated in Step 3.

## Step 5: Test the Implementation

Run the following command to test your SendGrid setup:

```python
python -m server.services.email_service
```

This will attempt to send a test email. Check the console output to verify it was sent successfully.

## Troubleshooting

If you encounter issues:

1. **Email not sending**: Check your API key and make sure sender verification is complete
2. **Emails going to spam**: Complete domain authentication in SendGrid
3. **Rate limiting**: Ensure you're staying within your SendGrid plan limits

## CAN-SPAM and CASL Compliance

As mentioned in the SendGrid interface, you need to ensure your emails comply with anti-spam laws:

1. Include your physical mailing address in the email footer
2. Provide a clear way to unsubscribe
3. Honor opt-out requests promptly

These requirements are built into the email template in the `email_service.py` file. 