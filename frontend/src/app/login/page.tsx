'use client'

import { useState } from 'react'
import { signIn, getSession } from 'next-auth/react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Logo } from '@/components/ui/logo'
import { BackNavigation } from '@/components/BackNavigation'
import { Mail, Lock } from 'lucide-react'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  
  const router = useRouter()
  const searchParams = useSearchParams()
  const callbackUrl = searchParams.get('callbackUrl') || '/dashboard'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    try {
      const result = await signIn('credentials', {
        email,
        password,
        redirect: false,
      })

      if (result?.error) {
        setError('Invalid email or password')
      } else {
        router.push(callbackUrl)
      }
    } catch (error) {
      setError('An error occurred. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleMicrosoftSignIn = async () => {
    setIsLoading(true)
    try {
      await signIn('azure-ad', { callbackUrl })
    } catch (error) {
      setError('Microsoft sign-in failed. Please try again.')
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-white flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <BackNavigation href="/" label="Back to Home" />
        <Card className="w-full border-gray-200 shadow-lg">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-6">
            <Logo iconOnly={true} size={48} />
          </div>
          <CardTitle className="text-clauseforge-primary font-legal text-2xl">Sign In</CardTitle>
          <CardDescription className="text-clauseforge-primary/70 font-legal">
            Enter your credentials to access your account
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-clauseforge-primary font-legal">Email</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-3 h-4 w-4 text-clauseforge-primary/50" />
                <Input
                  id="email"
                  type="email"
                  placeholder="Enter your email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-10 border-gray-200 text-clauseforge-primary font-legal focus:border-clauseforge-primary focus:ring-clauseforge-primary"
                  required
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="password" className="text-clauseforge-primary font-legal">Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-3 h-4 w-4 text-clauseforge-primary/50" />
                <Input
                  id="password"
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-10 border-gray-200 text-clauseforge-primary font-legal focus:border-clauseforge-primary focus:ring-clauseforge-primary"
                  required
                />
              </div>
            </div>

            {error && (
              <div className="text-sm text-red-600 bg-red-50 p-3 rounded-md font-legal">
                {error}
              </div>
            )}

            <Button 
              type="submit" 
              className="w-full bg-clauseforge-primary hover:bg-clauseforge-primary-hover text-white font-legal rounded-lg transition-colors" 
              disabled={isLoading}
            >
              {isLoading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>

          <div className="mt-4">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t border-gray-200" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-white px-2 text-clauseforge-primary/70 font-legal">Or continue with</span>
              </div>
            </div>
            
            <Button
              type="button"
              variant="outline"
              className="w-full mt-4 border-gray-200 text-clauseforge-primary hover:bg-clauseforge-primary/5 font-legal"
              onClick={handleMicrosoftSignIn}
              disabled={isLoading}
            >
              <svg className="w-4 h-4 mr-2" viewBox="0 0 23 23">
                <path fill="#f35325" d="M1 1h10v10H1z"/>
                <path fill="#81bc06" d="M12 1h10v10H12z"/>
                <path fill="#05a6f0" d="M1 12h10v10H1z"/>
                <path fill="#ffba08" d="M12 12h10v10H12z"/>
              </svg>
              Sign in with Microsoft
            </Button>
          </div>

          <div className="mt-6 text-center">
            <p className="text-sm text-clauseforge-primary/70 font-legal">
              Don't have an account?{' '}
              <Link href="/signup" className="text-clauseforge-primary hover:text-clauseforge-primary-hover font-medium transition-colors">
                Sign up
              </Link>
            </p>
          </div>
        </CardContent>
      </Card>
      </div>
    </div>
  )
}