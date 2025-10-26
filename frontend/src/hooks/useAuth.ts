/**
 * Authentication hooks and utilities
 */

import { useSession, signOut } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { useCallback } from 'react'

export function useAuth() {
  const { data: session, status } = useSession()
  const router = useRouter()

  const user = session?.user
  const isLoading = status === 'loading'
  const isAuthenticated = status === 'authenticated'
  const isUnauthenticated = status === 'unauthenticated'

  const logout = useCallback(async () => {
    await signOut({ 
      callbackUrl: '/auth/signin',
      redirect: true 
    })
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
      router.push('/auth/signin')
      return false
    }
    return true
  }, [isAuthenticated, isLoading, router])

  const requireRole = useCallback((role: string | string[]) => {
    if (!requireAuth()) return false
    
    if (!hasRole(role)) {
      router.push('/dashboard') // Redirect to dashboard if insufficient permissions
      return false
    }
    return true
  }, [requireAuth, hasRole, router])

  return {
    // Session data
    session,
    user,
    accessToken: session?.accessToken,
    
    // Status
    isLoading,
    isAuthenticated,
    isUnauthenticated,
    
    // Actions
    logout,
    
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