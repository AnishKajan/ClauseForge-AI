/**
 * NextAuth.js type extensions
 */

import { DefaultSession, DefaultUser } from 'next-auth'
import { JWT, DefaultJWT } from 'next-auth/jwt'

declare module 'next-auth' {
  interface Session {
    user: {
      id: string
      role: string
      orgId: string
      isActive: boolean
      emailVerified: boolean
      provider: string
    } & DefaultSession['user']
    accessToken: string
    error?: string
  }

  interface User extends DefaultUser {
    role: string
    orgId: string
    isActive: boolean
    emailVerified: boolean
    provider: string
    accessToken: string
    refreshToken: string
    expiresAt: number
  }
}

declare module 'next-auth/jwt' {
  interface JWT extends DefaultJWT {
    accessToken: string
    refreshToken: string
    expiresAt: number
    role: string
    orgId: string
    isActive: boolean
    emailVerified: boolean
    provider: string
    error?: string
  }
}