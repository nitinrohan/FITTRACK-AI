/**
 * Next.js edge middleware - route protection.
 *
 * Rules:
 * - /dashboard/* and /settings/* require the fittrack_access cookie.
 *   If absent, redirect to /auth/login?returnTo=<original-path>.
 * - /auth/login and /auth/register redirect to /dashboard when the user
 *   already has a cookie (avoids showing auth pages to signed-in users).
 *
 * Note:
 * - Middleware only checks for cookie *presence*, not JWT validity.
 *   The API validates the token on every request; if the token is expired
 *   the API returns 401 and the frontend clears state and redirects to login.
 * - This layer prevents the flash of unauthenticated UI on protected routes.
 *
 * Edge runtime limitations:
 * - Cannot use Node.js APIs or the ORM here.
 * - Keep this file lightweight; no database access.
 */

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const ACCESS_COOKIE = "fittrack_access";

/** Routes that require authentication. Matched as prefix. */
const PROTECTED_PREFIXES = ["/dashboard", "/settings", "/onboarding"];

/** Routes that should not be accessible to authenticated users. */
const AUTH_PATHS = ["/auth/login", "/auth/register"];

export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;
  const hasSession = request.cookies.has(ACCESS_COOKIE);

  // Redirect authenticated users away from auth pages.
  if (hasSession && AUTH_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  // Redirect unauthenticated users away from protected routes.
  if (!hasSession && PROTECTED_PREFIXES.some((p) => pathname.startsWith(p))) {
    const loginUrl = new URL("/auth/login", request.url);
    loginUrl.searchParams.set("returnTo", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Run middleware on all routes except:
     * - _next/static  (static files)
     * - _next/image   (image optimization)
     * - favicon.ico
     * - Public API routes (handled by FastAPI, not Next.js)
     */
    "/((?!_next/static|_next/image|favicon.ico|api/).*)",
  ],
};
