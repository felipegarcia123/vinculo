import { NextResponse, type NextRequest } from "next/server";

const pages = new Set(["/login", "/loyalty", "/loyalty/owner", "/loyalty/cashier"]);

export function proxy(request: NextRequest) {
  const cleanUrl = new URL(request.url);
  const rawParams = cleanUrl.search.slice(1).split("&").filter(Boolean);
  let removedChatGptSource = false;
  const remainingParams = rawParams.filter((part) => {
    const entry = new URLSearchParams(part).entries().next().value;
    const [key, value] = entry ?? ["", ""];
    if (key === "utm_source" && value === "chatgpt.com") {
      removedChatGptSource = true;
      return false;
    }
    return true;
  });
  if (removedChatGptSource) {
    cleanUrl.search = remainingParams.length ? `?${remainingParams.join("&")}` : "";
    return NextResponse.redirect(cleanUrl);
  }

  const path = request.nextUrl.pathname.replace(/\/$/, "") || "/";
  if (path === "/") return NextResponse.redirect(new URL("/login", request.url));
  if (pages.has(path)) return NextResponse.next();
  return new NextResponse(null, { status: 404, headers: { "Cache-Control": "no-store" } });
}

export const config = { matcher: ["/((?!api/v1|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|css|js)$).*)"] };
