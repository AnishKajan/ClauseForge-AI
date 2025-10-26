'use client';

import React, { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

export default function PaymentConfirmPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const clientSecret = searchParams.get('client_secret');
    const paymentIntent = searchParams.get('payment_intent');
    const paymentIntentClientSecret = searchParams.get('payment_intent_client_secret');
    
    if (clientSecret || paymentIntent) {
      // In a real implementation, you would:
      // 1. Use Stripe.js to confirm the payment
      // 2. Check the payment status
      // 3. Update the UI accordingly
      
      // For now, we'll simulate a successful payment
      setTimeout(() => {
        setStatus('success');
        setMessage('Your subscription has been activated successfully!');
      }, 2000);
    } else {
      setStatus('error');
      setMessage('Invalid payment confirmation link.');
    }
  }, [searchParams]);

  const handleReturnToBilling = () => {
    router.push('/billing');
  };

  const handleReturnToHome = () => {
    router.push('/');
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <Card className="max-w-md w-full p-8 text-center">
        {status === 'loading' && (
          <div className="space-y-4">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <h2 className="text-xl font-semibold">Confirming Payment...</h2>
            <p className="text-gray-600">Please wait while we process your payment.</p>
          </div>
        )}

        {status === 'success' && (
          <div className="space-y-4">
            <div className="mx-auto w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-green-800">Payment Successful!</h2>
            <p className="text-gray-600">{message}</p>
            <div className="space-y-2">
              <Button onClick={handleReturnToBilling} className="w-full">
                View Billing Dashboard
              </Button>
              <Button onClick={handleReturnToHome} variant="outline" className="w-full">
                Return to Home
              </Button>
            </div>
          </div>
        )}

        {status === 'error' && (
          <div className="space-y-4">
            <div className="mx-auto w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-red-800">Payment Failed</h2>
            <p className="text-gray-600">{message}</p>
            <div className="space-y-2">
              <Button onClick={handleReturnToBilling} className="w-full">
                Try Again
              </Button>
              <Button onClick={handleReturnToHome} variant="outline" className="w-full">
                Return to Home
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}