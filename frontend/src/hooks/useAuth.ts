/**
 * Client-side authentication hook for static export
 */

import { useRouter } from 'next/navigation'
import { useCallback, useEffect, useState } from 'react'

interface User {
  id: string
  email: string
  name?: string
  role?: string
  isActive?: boolean
  emailVerified?: boolean
  orgId?: string
  provider?: string
}

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    // Only run on client side
    if (typeof window === 'undefined') {
      setIsLoading(false)
      return
    }

    // Check for stored auth token and user data
    const token = localStorage.getItem('auth_token')
    const userData = localStorage.getItem('user_data')
    
    if (token && userData) {
      try {
        setUser(JSON.parse(userData))
      } catch (e) {
        localStorage.removeItem('auth_token')
        localStorage.removeItem('user_data')
      }
    }
    setIsLoading(false)
  }, [])

  const logout = useCallback(() => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('user_data')
    }
    setUser(null)
    router.push('/login')
  }, [router])

  const login = useCallback((token: string, userData: User) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', token)
      localStorage.setItem('user_data', JSON.stringify(userData))
    }
    setUser(userData)
  }, [])

  const hasRole = useCallback((role: string | string[]) => {
    if (!user?.role) return false
    
    const roles = Array.isArray(role) ? role : [role]
    return roles.includes(user.role)
  }, [user?.role])

  const hasMinimumRole = useCallback((minimumRole: string) => {
    if (!user?.role) return false

    const roleHierarchy = {
      'viewer': 0,
      'reviewer': 1,
      'admin': 2,
      'super_admin': 3,
    }

    const userRoleLevel = roleHierarchy[user.role as keyof typeof roleHierarchy] ?? -1
    const minimumRoleLevel = roleHierarchy[minimumRole as keyof typeof roleHierarchy] ?? 999

    return userRoleLevel >= minimumRoleLevel
  }, [user?.role])

  const requireAuth = useCallback(() => {
    if (!isAuthenticated && !isLoading) {
      router.push('/login')
      return false
    }
    return true
  }, [user, isLoading, router])

  const requireRole = useCallback((role: string | string[]) => {
    if (!requireAuth()) return false
    
    if (!hasRole(role)) {
      router.push('/dashboard')
      return false
    }
    return true
  }, [requireAuth, hasRole, router])

  const isAuthenticated = !!user
  const isUnauthenticated = !user && !isLoading

  return {
    // Session data
    session: user ? { user } : null,
    user,
    accessToken: typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null,
    
    // Status
    isLoading,
    isAuthenticated,
    isUnauthenticated,
    
    // Actions
    logout,
    login,
    
    // Permission checks
    hasRole,
    hasMinimumRole,
    requireAuth,
    requireRole,
    
    // User properties
    isActive: user?.isActive ?? false,
    isEmailVerified: user?.emailVerified ?? false,
    orgId: user?.orgId,
    role: user?.role,
    provider: user?.provider,
  }
}

export function useRequireAuth() {
  const auth = useAuth()
  
  if (!auth.requireAuth()) {
    return null
  }
  
  return auth
}

export function useRequireRole(role: string | string[]) {
  const auth = useAuth()
  
  if (!auth.requireRole(role)) {
    return null
  }
  
  return auth
}