import { NextResponse, type NextRequest } from "next/server";
import { stripChatgptUtmSource } from "@/lib/cleanChatgptUtm.mjs";

const pages = new Set(["/login", "/loyalty", "/loyalty/owner", "/loyalty/cashier"]);

export function proxy(request: NextRequest) {
  const cleanUrl = new URL(request.url);
  if (stripChatgptUtmSource(cleanUrl)) {
    return NextResponse.redirect(cleanUrl);
  }

  const path = request.nextUrl.pathname.replace(/\/$/, "") || "/";
  if (path === "/") return NextResponse.redirect(new URL("/login", request.url));
  if (pages.has(path)) return NextResponse.next();
  return new NextResponse(null, { status: 404, headers: { "Cache-Control": "no-store" } });
}

export const config = { matcher: ["/((?!api/v1|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|css|js)$).*)"] };
