'use client'

import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Logo } from '@/components/ui/logo'
import { BackNavigation } from '@/components/BackNavigation'
import { Check } from 'lucide-react'

export default function PricingPage() {
  const { user } = useAuth()
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(false)

  const handleUpgrade = async () => {
    if (!user) {
      router.push('/login?callbackUrl=/pricing')
      return
    }

    setIsLoading(true)
    try {
      const response = await fetch('/api/checkout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          priceId: process.env.NEXT_PUBLIC_STRIPE_PRICE_PRO || 'price_12345'
        }),
      })

      const data = await response.json()
      
      if (data.url) {
        window.location.href = data.url
      } else {
        throw new Error('Failed to create checkout session')
      }
    } catch (error) {
      console.error('Checkout error:', error)
      alert('Failed to start checkout. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white shadow-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Link href="/">
              <Logo size={32} showText={true} />
            </Link>
            <div className="flex items-center space-x-4">
              {user ? (
                <Button variant="ghost" asChild className="text-clauseforge-primary hover:bg-clauseforge-primary/5 font-legal">
                  <Link href="/dashboard">Dashboard</Link>
                </Button>
              ) : (
                <>
                  <Button variant="ghost" asChild className="text-clauseforge-primary hover:bg-clauseforge-primary/5 font-legal">
                    <Link href="/login">Sign In</Link>
                  </Button>
                  <Button asChild className="bg-clauseforge-primary hover:bg-clauseforge-primary-hover text-white font-legal">
                    <Link href="/signup">Get Started</Link>
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Pricing Section */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <BackNavigation href="/" label="Back to Home" />
          <div className="text-center mb-16">
            <h1 className="text-4xl font-bold text-clauseforge-primary mb-4 font-legal">
              Simple, Transparent Pricing
            </h1>
            <p className="text-xl text-clauseforge-primary/70 max-w-2xl mx-auto font-legal">
              Choose the plan that's right for your legal team
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            {/* Free Plan */}
            <Card className="relative border-gray-200 shadow-sm">
              <CardHeader>
                <CardTitle className="text-2xl text-clauseforge-primary font-legal">Free</CardTitle>
                <CardDescription className="text-clauseforge-primary/70 font-legal">Perfect for trying out ClauseForge</CardDescription>
                <div className="text-3xl font-bold text-clauseforge-primary font-legal">$0<span className="text-lg font-normal text-clauseforge-primary/70">/month</span></div>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3 mb-6">
                  <li className="flex items-center">
                    <Check className="h-5 w-5 text-clauseforge-primary mr-3" />
                    <span className="text-clauseforge-primary font-legal">5 document analyses per month</span>
                  </li>
                  <li className="flex items-center">
                    <Check className="h-5 w-5 text-clauseforge-primary mr-3" />
                    <span className="text-clauseforge-primary font-legal">Basic risk assessment</span>
                  </li>
                  <li className="flex items-center">
                    <Check className="h-5 w-5 text-clauseforge-primary mr-3" />
                    <span className="text-clauseforge-primary font-legal">Email support</span>
                  </li>
                </ul>
                <Button variant="outline" className="w-full border-clauseforge-primary text-clauseforge-primary hover:bg-clauseforge-primary hover:text-white font-legal" asChild>
                  <Link href="/signup">Get Started Free</Link>
                </Button>
              </CardContent>
            </Card>

            {/* Pro Plan */}
            <Card className="relative border-clauseforge-primary border-2 shadow-lg">
              <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                <span className="bg-clauseforge-primary text-white px-4 py-1 rounded-full text-sm font-medium font-legal">
                  Most Popular
                </span>
              </div>
              <CardHeader>
                <CardTitle className="text-2xl text-clauseforge-primary font-legal">Pro</CardTitle>
                <CardDescription className="text-clauseforge-primary/70 font-legal">For professional legal teams</CardDescription>
                <div className="text-3xl font-bold text-clauseforge-primary font-legal">$49<span className="text-lg font-normal text-clauseforge-primary/70">/month</span></div>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3 mb-6">
                  <li className="flex items-center">
                    <Check className="h-5 w-5 text-clauseforge-primary mr-3" />
                    <span className="text-clauseforge-primary font-legal">Unlimited document analyses</span>
                  </li>
                  <li className="flex items-center">
                    <Check className="h-5 w-5 text-clauseforge-primary mr-3" />
                    <span className="text-clauseforge-primary font-legal">Advanced risk assessment</span>
                  </li>
                  <li className="flex items-center">
                    <Check className="h-5 w-5 text-clauseforge-primary mr-3" />
                    <span className="text-clauseforge-primary font-legal">Smart Q&A with documents</span>
                  </li>
                  <li className="flex items-center">
                    <Check className="h-5 w-5 text-clauseforge-primary mr-3" />
                    <span className="text-clauseforge-primary font-legal">Team collaboration</span>
                  </li>
                  <li className="flex items-center">
                    <Check className="h-5 w-5 text-clauseforge-primary mr-3" />
                    <span className="text-clauseforge-primary font-legal">Priority support</span>
                  </li>
                  <li className="flex items-center">
                    <Check className="h-5 w-5 text-clauseforge-primary mr-3" />
                    <span className="text-clauseforge-primary font-legal">API access</span>
                  </li>
                </ul>
                <Button 
                  className="w-full bg-clauseforge-primary hover:bg-clauseforge-primary-hover text-white font-legal" 
                  onClick={handleUpgrade}
                  disabled={isLoading}
                >
                  {isLoading ? 'Processing...' : 'Upgrade to Pro'}
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>
    </div>
  )
}