import { withAuth } from "next-auth/middleware";
import { NextResponse } from "next/server";

export default withAuth(
  function middleware(req) {
    const token = req.nextauth.token;
    const isAuth = !!token;
    const pathname = req.nextUrl.pathname;

    // Protected routes that require authentication
    const protectedRoutes = ["/dashboard", "/app", "/workspace", "/billing"];
    const isProtectedRoute = protectedRoutes.some((route) =>
      pathname.startsWith(route)
    );

    // Redirect unauthenticated users from protected routes to login
    if (isProtectedRoute && !isAuth) {
      const callbackUrl = encodeURIComponent(req.url);
      return NextResponse.redirect(
        new URL(`/login?callbackUrl=${callbackUrl}`, req.url)
      );
    }

    // Redirect authenticated users away from auth pages
    if ((pathname === "/login" || pathname === "/signup") && isAuth) {
      return NextResponse.redirect(new URL("/dashboard", req.url));
    }

    return NextResponse.next();
  },
  {
    callbacks: {
      authorized: ({ token, req }) => {
        const pathname = req.nextUrl.pathname;

        // Always allow access to public pages
        const publicPages = ["/", "/pricing", "/demo", "/login", "/signup"];
        const isPublicPage =
          publicPages.includes(pathname) ||
          pathname.startsWith("/features/") ||
          pathname.startsWith("/api/auth") ||
          pathname.startsWith("/_next") ||
          pathname.startsWith("/favicon");

        if (isPublicPage) {
          return true;
        }

        // Protected routes require authentication
        const protectedRoutes = [
          "/dashboard",
          "/app",
          "/workspace",
          "/billing",
        ];
        const isProtectedRoute = protectedRoutes.some((route) =>
          pathname.startsWith(route)
        );

        if (isProtectedRoute) {
          return !!token;
        }

        // Allow all other routes by default
        return true;
      },
    },
  }
);

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
