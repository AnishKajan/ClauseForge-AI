'use client'

import { useAuth } from '@/hooks/useAuth'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'

interface AuthGuardProps {
  children: React.ReactNode
  requireAuth?: boolean
  requiredRole?: string | string[]
  fallback?: React.ReactNode
}

export function AuthGuard({ 
  children, 
  requireAuth = true, 
  requiredRole,
  fallback = <div>Loading...</div>
}: AuthGuardProps) {
  const { isAuthenticated, isLoading, hasRole } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!isLoading && requireAuth && !isAuthenticated) {
      router.push('/login')
    }
  }, [isLoading, requireAuth, isAuthenticated, router])

  if (isLoading) {
    return <>{fallback}</>
  }

  if (requireAuth && !isAuthenticated) {
    return <>{fallback}</>
  }

  if (requiredRole && !hasRole(requiredRole)) {
    return <div>Access denied. Insufficient permissions.</div>
  }

  return <>{children}</>
}