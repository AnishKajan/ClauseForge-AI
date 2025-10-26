'use client'

import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { BackNavigation } from '@/components/BackNavigation'
import { apiFetch } from '@/lib/api'

export default function TestSSOPage() {
  const { user, accessToken } = useAuth()
  const [apiResponse, setApiResponse] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const testSecureEndpoint = async () => {
    setIsLoading(true)
    setError('')
    setApiResponse(null)

    try {
      const response = await apiFetch('/api/secure')
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      
      const data = await response.json()
      setApiResponse(data)
    } catch (err: any) {
      setError(err.message || 'Failed to call secure endpoint')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-white p-4">
      <div className="container mx-auto max-w-2xl">
        <BackNavigation href="/dashboard" label="Back to Dashboard" />
        
        <Card className="border-gray-200 shadow-lg">
          <CardHeader>
            <CardTitle className="text-clauseforge-primary font-legal">SSO Test Page</CardTitle>
            <CardDescription className="text-clauseforge-primary/70 font-legal">
              Test Microsoft Entra ID authentication with FastAPI backend
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Session Info */}
            <div>
              <h3 className="text-lg font-semibold text-clauseforge-primary mb-2">Session Status</h3>
              {user ? (
                <div className="bg-green-50 p-4 rounded-lg">
                  <p className="text-green-800 font-medium">✅ Authenticated</p>
                  <p className="text-sm text-green-700 mt-1">
                    Email: {user.email}
                  </p>
                  {accessToken && (
                    <p className="text-xs text-green-600 mt-1">
                      Token: {accessToken.substring(0, 50)}...
                    </p>
                  )}
                </div>
              ) : (
                <div className="bg-red-50 p-4 rounded-lg">
                  <p className="text-red-800 font-medium">❌ Not authenticated</p>
                  <p className="text-sm text-red-700 mt-1">
                    Please sign in to test the secure endpoint
                  </p>
                </div>
              )}
            </div>

            {/* API Test */}
            <div>
              <h3 className="text-lg font-semibold text-clauseforge-primary mb-2">Secure API Test</h3>
              <Button
                onClick={testSecureEndpoint}
                disabled={!user || isLoading}
                className="bg-clauseforge-primary hover:bg-clauseforge-primary-hover text-white font-legal"
              >
                {isLoading ? 'Testing...' : 'Test Secure Endpoint'}
              </Button>
              
              {error && (
                <div className="mt-4 bg-red-50 p-4 rounded-lg">
                  <p className="text-red-800 font-medium">Error:</p>
                  <p className="text-sm text-red-700 mt-1">{error}</p>
                </div>
              )}
              
              {apiResponse && (
                <div className="mt-4 bg-blue-50 p-4 rounded-lg">
                  <p className="text-blue-800 font-medium">API Response:</p>
                  <pre className="text-sm text-blue-700 mt-1 overflow-x-auto">
                    {JSON.stringify(apiResponse, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            {/* Instructions */}
            <div className="bg-gray-50 p-4 rounded-lg">
              <h4 className="font-semibold text-clauseforge-primary mb-2">Test Instructions:</h4>
              <ol className="text-sm text-clauseforge-primary/70 space-y-1 list-decimal list-inside">
                <li>Sign in using Microsoft Entra ID</li>
                <li>Click "Test Secure Endpoint" to call the protected FastAPI route</li>
                <li>Verify that the API returns user information from the JWT token</li>
              </ol>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}