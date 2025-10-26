# Stripe Webhook Configuration Guide

This guide covers setting up Stripe webhooks for LexiScan billing integration.

## Prerequisites

1. Stripe account (https://stripe.com)
2. LexiScan application deployed with webhook endpoint

## Webhook Endpoint Setup

### 1. Webhook URL
Configure your webhook endpoint URL in Stripe Dashboard:
```
https://your-domain.com/api/webhooks/stripe
```

For local development:
```
http://localhost:8000/api/webhooks/stripe
```

### 2. Required Events

Configure Stripe to send the following events to your webhook:

#### Subscription Events
- `customer.subscription.created`
- `customer.subscription.updated` 
- `customer.subscription.deleted`
- `customer.subscription.trial_will_end`

#### Payment Events
- `invoice.payment_succeeded`
- `invoice.payment_failed`
- `invoice.created`
- `invoice.finalized`

#### Customer Events
- `customer.created`
- `customer.updated`
- `customer.deleted`

#### Usage Events (for metered billing)
- `usage_record.created`

### 3. Webhook Configuration Steps

1. **Login to Stripe Dashboard**
   - Go to https://dashboard.stripe.com
   - Navigate to Developers → Webhooks

2. **Create Webhook Endpoint**
   - Click "Add endpoint"
   - Enter your webhook URL
   - Select "Latest API version"

3. **Configure Events**
   - Click "Select events"
   - Choose the events listed above
   - Save the configuration

4. **Get Webhook Secret**
   - After creating the webhook, click on it
   - Copy the "Signing secret" (starts with `whsec_`)
   - Add this to your environment variables

## Environment Variables

Add these to your `.env` file:

```bash
# Stripe Configuration
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here

# Webhook endpoint (for reference)
STRIPE_WEBHOOK_ENDPOINT=https://your-domain.com/api/webhooks/stripe
```

## Product and Price Configuration

### 1. Create Products in Stripe

Create the following products in your Stripe Dashboard:

#### Free Tier
- **Product Name**: "LexiScan Free"
- **Type**: Recurring
- **Billing Period**: Monthly
- **Price**: $0.00
- **Metadata**: 
  - `plan_type`: `free`
  - `pages_limit`: `50`
  - `queries_limit`: `100`

#### Pro Tier
- **Product Name**: "LexiScan Pro"
- **Type**: Recurring
- **Billing Period**: Monthly
- **Price**: $29.00
- **Metadata**:
  - `plan_type`: `pro`
  - `pages_limit`: `1500`
  - `queries_limit`: `1000`

#### Enterprise Tier
- **Product Name**: "LexiScan Enterprise"
- **Type**: Recurring
- **Billing Period**: Monthly
- **Price**: $199.00
- **Metadata**:
  - `plan_type`: `enterprise`
  - `pages_limit`: `unlimited`
  - `queries_limit`: `unlimited`

### 2. Usage-Based Pricing (Optional)

For overage charges, create additional products:

#### Page Processing Overage
- **Product Name**: "Additional Pages"
- **Type**: One-time
- **Price**: $0.10 per page
- **Metadata**: `usage_type`: `pages`

#### Query Overage
- **Product Name**: "Additional Queries"
- **Type**: One-time
- **Price**: $0.05 per query
- **Metadata**: `usage_type`: `queries`

## Testing Webhooks

### 1. Local Development with ngrok

For local testing, use ngrok to expose your local server:

```bash
# Install ngrok
brew install ngrok

# Expose local server
ngrok http 8000

# Use the ngrok URL in Stripe webhook configuration
# Example: https://abc123.ngrok.io/api/webhooks/stripe
```

### 2. Webhook Testing

Use Stripe CLI to test webhooks locally:

```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe

# Login to Stripe
stripe login

# Forward webhooks to local server
stripe listen --forward-to localhost:8000/api/webhooks/stripe

# Trigger test events
stripe trigger customer.subscription.created
stripe trigger invoice.payment_succeeded
```

### 3. Webhook Verification

Your webhook endpoint should:

1. **Verify the signature** using the webhook secret
2. **Handle idempotency** by storing processed event IDs
3. **Return 200 status** for successful processing
4. **Return 4xx/5xx** for errors (Stripe will retry)

Example verification code:
```python
import stripe
import hmac
import hashlib

def verify_webhook_signature(payload, signature, secret):
    try:
        stripe.Webhook.construct_event(payload, signature, secret)
        return True
    except ValueError:
        # Invalid payload
        return False
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return False
```

## Webhook Event Handling

### Customer Subscription Events

```python
def handle_subscription_created(event):
    subscription = event['data']['object']
    customer_id = subscription['customer']
    plan_id = subscription['items']['data'][0]['price']['id']
    
    # Update user's subscription in database
    # Set plan limits based on plan_id
    # Send welcome email

def handle_subscription_updated(event):
    subscription = event['data']['object']
    # Handle plan changes, cancellations, etc.

def handle_subscription_deleted(event):
    subscription = event['data']['object']
    # Downgrade user to free tier
    # Send cancellation email
```

### Payment Events

```python
def handle_payment_succeeded(event):
    invoice = event['data']['object']
    customer_id = invoice['customer']
    
    # Update payment status
    # Reset usage counters for new billing period
    # Send receipt email

def handle_payment_failed(event):
    invoice = event['data']['object']
    # Handle failed payment
    # Send payment failure notification
    # Potentially suspend account
```

## Security Best Practices

1. **Always verify webhook signatures**
2. **Use HTTPS for webhook endpoints**
3. **Implement idempotency checks**
4. **Log all webhook events for debugging**
5. **Handle webhook retries gracefully**
6. **Keep webhook secrets secure**

## Monitoring and Debugging

1. **Stripe Dashboard**: Monitor webhook delivery status
2. **Application Logs**: Log all webhook processing
3. **Error Tracking**: Monitor webhook failures
4. **Retry Logic**: Handle temporary failures

## Production Checklist

- [ ] Webhook endpoint is accessible via HTTPS
- [ ] All required events are configured
- [ ] Webhook secret is stored securely
- [ ] Signature verification is implemented
- [ ] Idempotency handling is in place
- [ ] Error handling and logging are configured
- [ ] Products and prices are created in Stripe
- [ ] Test webhooks are working correctly
- [ ] Monitoring and alerting are set up