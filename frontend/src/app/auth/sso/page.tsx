'use client'

import React, { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { signIn } from 'next-auth/react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export default function SSOLoginPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [orgId, setOrgId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    // Get org ID from URL params
    const orgIdParam = searchParams.get('org_id')
    if (orgIdParam) {
      setOrgId(orgIdParam)
    }
  }, [searchParams])

  const handleSSOLogin = async () => {
    if (!orgId) {
      setError('Organization ID is required')
      return
    }

    setLoading(true)
    setError('')

    try {
      // Initiate SSO login
      const response = await fetch(`/api/sso/login/${orgId}`)
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to initiate SSO login')
      }

      const { authorization_url } = await response.json()
      
      // Redirect to SSO provider
      window.location.href = authorization_url
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
      setLoading(false)
    }
  }

  const handleManualLogin = () => {
    router.push('/auth/signin')
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Enterprise Sign In
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Sign in with your organization's SSO provider
          </p>
        </div>

        <Card className="p-8">
          <div className="space-y-6">
            <div>
              <label htmlFor="orgId" className="block text-sm font-medium text-gray-700">
                Organization ID
              </label>
              <input
                id="orgId"
                name="orgId"
                type="text"
                value={orgId}
                onChange={(e) => setOrgId(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="Enter your organization ID"
              />
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                {error}
              </div>
            )}

            <div className="space-y-3">
              <Button
                onClick={handleSSOLogin}
                disabled={loading || !orgId}
                className="w-full"
              >
                {loading ? 'Redirecting...' : 'Sign in with SSO'}
              </Button>

              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-300" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-white text-gray-500">Or</span>
                </div>
              </div>

              <Button
                variant="outline"
                onClick={handleManualLogin}
                className="w-full"
              >
                Sign in with Email
              </Button>
            </div>
          </div>
        </Card>

        <div className="text-center">
          <p className="text-sm text-gray-600">
            Don't have an organization ID?{' '}
            <a href="/contact" className="font-medium text-blue-600 hover:text-blue-500">
              Contact support
            </a>
          </p>
        </div>
      </div>
    </div>
  )
}