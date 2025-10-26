/**
 * Authentication error page
 */

'use client'

import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function AuthErrorPage() {
  const searchParams = useSearchParams()
  const error = searchParams.get('error')

  const getErrorMessage = (error: string | null): { title: string; description: string } => {
    switch (error) {
      case 'Configuration':
        return {
          title: 'Server Configuration Error',
          description: 'There is a problem with the server configuration. Please contact support.',
        }
      case 'AccessDenied':
        return {
          title: 'Access Denied',
          description: 'You do not have permission to sign in with this account.',
        }
      case 'Verification':
        return {
          title: 'Verification Error',
          description: 'The verification token has expired or has already been used.',
        }
      case 'OAuthSignin':
      case 'OAuthCallback':
      case 'OAuthCreateAccount':
      case 'EmailCreateAccount':
        return {
          title: 'OAuth Error',
          description: 'There was an error with the OAuth provider. Please try again.',
        }
      case 'OAuthAccountNotLinked':
        return {
          title: 'Account Not Linked',
          description: 'This account is not linked to your existing account. Please sign in with your original provider.',
        }
      case 'EmailSignin':
        return {
          title: 'Email Sign-in Error',
          description: 'There was an error sending the sign-in email. Please try again.',
        }
      case 'CredentialsSignin':
        return {
          title: 'Invalid Credentials',
          description: 'The email or password you entered is incorrect. Please try again.',
        }
      case 'SessionRequired':
        return {
          title: 'Session Required',
          description: 'You must be signed in to access this page.',
        }
      default:
        return {
          title: 'Authentication Error',
          description: 'An unexpected error occurred during authentication. Please try again.',
        }
    }
  }

  const { title, description } = getErrorMessage(error)

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900">LexiScan</h1>
          <p className="mt-2 text-gray-600">AI-powered contract analysis</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-red-600">{title}</CardTitle>
            <CardDescription>{description}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col space-y-2">
              <Button asChild>
                <Link href="/auth/signin">
                  Try signing in again
                </Link>
              </Button>
              
              <Button variant="outline" asChild>
                <Link href="/">
                  Go to homepage
                </Link>
              </Button>
            </div>

            {error && (
              <div className="mt-4 p-3 bg-gray-100 rounded text-sm text-gray-600">
                <strong>Error code:</strong> {error}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}