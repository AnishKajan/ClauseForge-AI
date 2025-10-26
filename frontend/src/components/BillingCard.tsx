'use client';

import React, { useState, useEffect } from 'react';
import { Card } from './ui/card';
import { Button } from './ui/button';

interface Plan {
  name: string;
  price: number;
  currency: string;
  interval: string;
  features: string[];
  limits: {
    pages_per_month: number;
    tokens_per_month: number;
    documents_per_month: number;
  };
}

interface UsageSummary {
  plan: string;
  limits: {
    pages_per_month: number;
    tokens_per_month: number;
    documents_per_month: number;
  };
  usage: {
    pages: number;
    tokens: number;
    documents: number;
  };
  remaining: {
    pages_per_month: number;
    tokens_per_month: number;
    documents_per_month: number;
  };
  percentage_used: {
    pages_per_month: number;
    tokens_per_month: number;
    documents_per_month: number;
  };
}

interface SubscriptionInfo {
  plan: string;
  status: string;
  usage_limits: {
    pages_per_month: number;
    tokens_per_month: number;
    documents_per_month: number;
  };
  stripe_customer_id?: string;
  created_at: string;
}

export default function BillingCard() {
  const [plans, setPlans] = useState<Record<string, Plan>>({});
  const [currentSubscription, setCurrentSubscription] = useState<SubscriptionInfo | null>(null);
  const [usageSummary, setUsageSummary] = useState<UsageSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [upgrading, setUpgrading] = useState<string | null>(null);

  useEffect(() => {
    fetchBillingData();
  }, []);

  const fetchBillingData = async () => {
    try {
      setLoading(true);
      
      // Fetch available plans
      const plansResponse = await fetch('/api/billing/plans');
      const plansData = await plansResponse.json();
      
      if (plansData.success) {
        setPlans(plansData.data);
      }

      // Fetch current subscription
      const subscriptionResponse = await fetch('/api/billing/subscription', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });
      const subscriptionData = await subscriptionResponse.json();
      
      if (subscriptionData.success) {
        setCurrentSubscription(subscriptionData.data);
      }

      // Fetch usage summary
      const usageResponse = await fetch('/api/billing/usage', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });
      const usageData = await usageResponse.json();
      
      if (usageData.success) {
        setUsageSummary(usageData.data);
      }

    } catch (err) {
      setError('Failed to load billing information');
      console.error('Error fetching billing data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (planName: string, priceId: string) => {
    try {
      setUpgrading(planName);
      
      // Create Stripe customer if needed
      if (!currentSubscription?.stripe_customer_id) {
        const customerResponse = await fetch('/api/billing/customers', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          },
          body: JSON.stringify({
            email: 'user@example.com', // This should come from user context
            name: 'Organization Name' // This should come from org context
          })
        });
        
        if (!customerResponse.ok) {
          throw new Error('Failed to create customer');
        }
      }

      // Create subscription
      const subscriptionResponse = await fetch('/api/billing/subscriptions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({
          price_id: priceId
        })
      });

      const subscriptionData = await subscriptionResponse.json();
      
      if (subscriptionData.success) {
        // Handle successful subscription creation
        // This might involve redirecting to Stripe Checkout or handling payment
        if (subscriptionData.data.client_secret) {
          // Redirect to payment confirmation
          window.location.href = `/billing/confirm?client_secret=${subscriptionData.data.client_secret}`;
        } else {
          // Refresh billing data
          await fetchBillingData();
        }
      } else {
        throw new Error(subscriptionData.message || 'Failed to create subscription');
      }

    } catch (err) {
      setError(`Failed to upgrade to ${planName}: ${err instanceof Error ? err.message : 'Unknown error'}`);
      console.error('Error upgrading plan:', err);
    } finally {
      setUpgrading(null);
    }
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat().format(num);
  };

  const getUsagePercentage = (used: number, limit: number) => {
    return limit > 0 ? Math.min((used / limit) * 100, 100) : 0;
  };

  const getUsageColor = (percentage: number) => {
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 75) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-64 bg-gray-200 rounded-lg"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">{error}</p>
        <Button 
          onClick={fetchBillingData} 
          className="mt-2"
          variant="outline"
        >
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Current Usage Summary */}
      {usageSummary && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Current Usage</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Pages</span>
                <span>{formatNumber(usageSummary.usage.pages)} / {formatNumber(usageSummary.limits.pages_per_month)}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className={`h-2 rounded-full ${getUsageColor(usageSummary.percentage_used.pages_per_month)}`}
                  style={{ width: `${usageSummary.percentage_used.pages_per_month}%` }}
                ></div>
              </div>
              <p className="text-xs text-gray-600">
                {usageSummary.percentage_used.pages_per_month.toFixed(1)}% used
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Tokens</span>
                <span>{formatNumber(usageSummary.usage.tokens)} / {formatNumber(usageSummary.limits.tokens_per_month)}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className={`h-2 rounded-full ${getUsageColor(usageSummary.percentage_used.tokens_per_month)}`}
                  style={{ width: `${usageSummary.percentage_used.tokens_per_month}%` }}
                ></div>
              </div>
              <p className="text-xs text-gray-600">
                {usageSummary.percentage_used.tokens_per_month.toFixed(1)}% used
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Documents</span>
                <span>{formatNumber(usageSummary.usage.documents)} / {formatNumber(usageSummary.limits.documents_per_month)}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className={`h-2 rounded-full ${getUsageColor(usageSummary.percentage_used.documents_per_month)}`}
                  style={{ width: `${usageSummary.percentage_used.documents_per_month}%` }}
                ></div>
              </div>
              <p className="text-xs text-gray-600">
                {usageSummary.percentage_used.documents_per_month.toFixed(1)}% used
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Plan Comparison */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Choose Your Plan</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {Object.entries(plans).map(([planKey, plan]) => (
            <Card 
              key={planKey} 
              className={`p-6 relative ${
                currentSubscription?.plan === planKey 
                  ? 'ring-2 ring-blue-500 bg-blue-50' 
                  : ''
              }`}
            >
              {currentSubscription?.plan === planKey && (
                <div className="absolute top-4 right-4">
                  <span className="bg-blue-500 text-white px-2 py-1 rounded-full text-xs">
                    Current Plan
                  </span>
                </div>
              )}

              <div className="text-center mb-6">
                <h3 className="text-xl font-semibold mb-2">{plan.name}</h3>
                <div className="text-3xl font-bold">
                  ${plan.price}
                  <span className="text-lg font-normal text-gray-600">/{plan.interval}</span>
                </div>
              </div>

              <ul className="space-y-2 mb-6">
                {plan.features.map((feature, index) => (
                  <li key={index} className="flex items-center text-sm">
                    <svg className="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                    {feature}
                  </li>
                ))}
              </ul>

              <div className="space-y-2 mb-6 text-xs text-gray-600">
                <div className="flex justify-between">
                  <span>Pages per month:</span>
                  <span>{formatNumber(plan.limits.pages_per_month)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Tokens per month:</span>
                  <span>{formatNumber(plan.limits.tokens_per_month)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Documents per month:</span>
                  <span>{formatNumber(plan.limits.documents_per_month)}</span>
                </div>
              </div>

              {currentSubscription?.plan === planKey ? (
                <Button disabled className="w-full">
                  Current Plan
                </Button>
              ) : planKey === 'free' ? (
                <Button 
                  variant="outline" 
                  className="w-full"
                  onClick={() => {/* Handle downgrade to free */}}
                >
                  Downgrade
                </Button>
              ) : (
                <Button 
                  className="w-full"
                  onClick={() => handleUpgrade(plan.name, `price_${planKey}`)}
                  disabled={upgrading === planKey}
                >
                  {upgrading === planKey ? 'Processing...' : `Upgrade to ${plan.name}`}
                </Button>
              )}
            </Card>
          ))}
        </div>
      </div>

      {/* Current Subscription Details */}
      {currentSubscription && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Subscription Details</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-600">Current Plan</p>
              <p className="font-semibold capitalize">{currentSubscription.plan}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Status</p>
              <p className={`font-semibold capitalize ${
                currentSubscription.status === 'active' ? 'text-green-600' : 'text-red-600'
              }`}>
                {currentSubscription.status}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Subscription Started</p>
              <p className="font-semibold">
                {new Date(currentSubscription.created_at).toLocaleDateString()}
              </p>
            </div>
            {currentSubscription.stripe_customer_id && (
              <div>
                <p className="text-sm text-gray-600">Customer ID</p>
                <p className="font-mono text-sm">{currentSubscription.stripe_customer_id}</p>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}