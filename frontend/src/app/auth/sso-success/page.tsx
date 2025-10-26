'use client'

import React, { useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { signIn } from 'next-auth/react'

export default function SSOSuccessPage() {
  const router = useRouter()
  const searchParams = useSearchParams()

  useEffect(() => {
    const handleSSOSuccess = async () => {
      const accessToken = searchParams.get('access_token')
      const refreshToken = searchParams.get('refresh_token')

      if (accessToken && refreshToken) {
        // Store tokens in localStorage temporarily
        localStorage.setItem('access_token', accessToken)
        localStorage.setItem('refresh_token', refreshToken)

        // Sign in with NextAuth using the tokens
        const result = await signIn('credentials', {
          token: accessToken,
          redirect: false,
        })

        if (result?.ok) {
          router.push('/dashboard')
        } else {
          router.push('/auth/error?error=SSO authentication failed')
        }
      } else {
        router.push('/auth/error?error=Missing authentication tokens')
      }
    }

    // Listen for messages from SSO popup
    const handleMessage = (event: MessageEvent) => {
      if (event.data.type === 'SSO_SUCCESS') {
        localStorage.setItem('access_token', event.data.access_token)
        localStorage.setItem('refresh_token', event.data.refresh_token)
        
        signIn('credentials', {
          token: event.data.access_token,
          redirect: false,
        }).then((result) => {
          if (result?.ok) {
            router.push('/dashboard')
          } else {
            router.push('/auth/error?error=SSO authentication failed')
          }
        })
      }
    }

    window.addEventListener('message', handleMessage)
    handleSSOSuccess()

    return () => {
      window.removeEventListener('message', handleMessage)
    }
  }, [router, searchParams])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
        <h2 className="mt-4 text-xl font-semibold text-gray-900">
          Completing sign in...
        </h2>
        <p className="mt-2 text-gray-600">
          Please wait while we complete your authentication.
        </p>
      </div>
    </div>
  )
}