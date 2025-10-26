'use client';

import React, { useState } from 'react';
import Navigation from '../../components/Navigation';
import BillingCard from '../../components/BillingCard';
import UsageDashboard from '../../components/UsageDashboard';
import { Button } from '../../components/ui/button';

export default function BillingPage() {
  const [activeTab, setActiveTab] = useState<'usage' | 'plans' | 'payment'>('usage');

  const tabs = [
    { id: 'usage', label: 'Usage Dashboard', icon: '📊' },
    { id: 'plans', label: 'Plans & Billing', icon: '💳' },
    { id: 'payment', label: 'Payment Methods', icon: '🏦' }
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Billing & Usage</h1>
          <p className="mt-2 text-gray-600">
            Manage your subscription, monitor usage, and view billing information.
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-gray-200 mb-8">
          <nav className="-mb-px flex space-x-8">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`py-2 px-1 border-b-2 font-medium text-sm whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="bg-white rounded-lg shadow-sm">
          {activeTab === 'usage' && (
            <div className="p-6">
              <UsageDashboard />
            </div>
          )}

          {activeTab === 'plans' && (
            <div className="p-6">
              <BillingCard />
            </div>
          )}

          {activeTab === 'payment' && (
            <div className="p-6">
              <PaymentMethodsSection />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function PaymentMethodsSection() {
  const [paymentMethods, setPaymentMethods] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleAddPaymentMethod = async () => {
    // This would integrate with Stripe Elements or redirect to Stripe Checkout
    // For now, it's a placeholder
    alert('Payment method management would be implemented with Stripe Elements');
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Payment Methods</h2>
        <Button onClick={handleAddPaymentMethod}>
          Add Payment Method
        </Button>
      </div>

      {paymentMethods.length === 0 ? (
        <div className="text-center py-12">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">No payment methods</h3>
          <p className="mt-1 text-sm text-gray-500">
            Add a payment method to manage your subscription.
          </p>
          <div className="mt-6">
            <Button onClick={handleAddPaymentMethod}>
              Add Payment Method
            </Button>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Payment methods would be listed here */}
        </div>
      )}

      {/* Invoice History Section */}
      <div className="border-t pt-6">
        <h3 className="text-lg font-semibold mb-4">Invoice History</h3>
        <div className="text-center py-8">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <h4 className="mt-2 text-sm font-medium text-gray-900">No invoices yet</h4>
          <p className="mt-1 text-sm text-gray-500">
            Your invoice history will appear here once you have a paid subscription.
          </p>
        </div>
      </div>
    </div>
  );
}