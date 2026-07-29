import createMiddleware from "next-intl/middleware";
import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { routing } from "./i18n/routing";

const PUBLIC_PATHS = ["/login", "/signup", "/callback"];
const LEGAL_PATHS = ["/terms", "/privacy", "/legal"];

function getCleanPath(pathname: string): string {
  return pathname.replace(/^\/(en|fr)/, "") || "/";
}

function isPublicPath(pathname: string): boolean {
  const cleanPath = getCleanPath(pathname);
  return (
    cleanPath === "/"
    || PUBLIC_PATHS.some((p) => cleanPath.startsWith(p))
    || LEGAL_PATHS.some((p) => cleanPath.startsWith(p))
  );
}

function isAuthPath(pathname: string): boolean {
  const cleanPath = getCleanPath(pathname);
  return PUBLIC_PATHS.some((p) => cleanPath.startsWith(p));
}

const intlMiddleware = createMiddleware(routing);

export async function proxy(request: NextRequest) {
  // 1. Résoudre la locale via next-intl
  const intlResponse = intlMiddleware(request);

  // Si redirect de locale, laisser passer immédiatement
  if (intlResponse.status === 307 || intlResponse.status === 308) {
    return intlResponse;
  }

  // 2. Rafraîchir la session Supabase sur la réponse intl
  const response = intlResponse;

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value),
          );
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options),
          );
        },
      },
    },
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();

  const { pathname } = request.nextUrl;

  // User non connecté sur route protégée → /login
  if (!user && !isPublicPath(pathname)) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }

  // User connecté sur page auth → /workspaces (la landing reste accessible aux loggés)
  if (user && isAuthPath(pathname)) {
    const url = request.nextUrl.clone();
    url.pathname = "/workspaces";
    return NextResponse.redirect(url);
  }

  return response;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
