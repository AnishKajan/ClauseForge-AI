/**
 * NextAuth.js middleware for route protection
 */

import { withAuth } from 'next-auth/middleware'
import { NextResponse } from 'next/server'

export default withAuth(
  function middleware(req) {
    const token = req.nextauth.token
    const isAuth = !!token
    const isAuthPage = req.nextUrl.pathname.startsWith('/auth')
    const isPublicPage = req.nextUrl.pathname === '/' || req.nextUrl.pathname.startsWith('/public')

    // Redirect authenticated users away from auth pages
    if (isAuthPage && isAuth) {
      return NextResponse.redirect(new URL('/dashboard', req.url))
    }

    // Redirect unauthenticated users to sign-in page
    if (!isAuthPage && !isPublicPage && !isAuth) {
      let from = req.nextUrl.pathname
      if (req.nextUrl.search) {
        from += req.nextUrl.search
      }

      return NextResponse.redirect(
        new URL(`/auth/signin?callbackUrl=${encodeURIComponent(from)}`, req.url)
      )
    }

    // Check user permissions for admin routes
    if (req.nextUrl.pathname.startsWith('/admin')) {
      if (!token?.role || !['admin', 'super_admin'].includes(token.role as string)) {
        return NextResponse.redirect(new URL('/dashboard', req.url))
      }
    }

    // Check if user account is active
    if (isAuth && token?.isActive === false) {
      return NextResponse.redirect(new URL('/auth/error?error=AccessDenied', req.url))
    }

    return NextResponse.next()
  },
  {
    callbacks: {
      authorized: ({ token, req }) => {
        // Allow access to public pages and auth pages
        if (req.nextUrl.pathname === '/' || 
            req.nextUrl.pathname.startsWith('/auth') ||
            req.nextUrl.pathname.startsWith('/public') ||
            req.nextUrl.pathname.startsWith('/api/auth')) {
          return true
        }

        // Require authentication for all other pages
        return !!token
      },
    },
  }
)

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    '/((?!_next/static|_next/image|favicon.ico|public).*)',
  ],
}