/**
 * API Route Proxy — Download full project package from VPS over HTTPS.
 *
 * The browser cannot reliably fetch the HTTP VPS directly from the HTTPS app.
 * This keeps auth intact and streams the ZIP through the Next server.
 */
import * as Sentry from "@sentry/nextjs";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 300;

async function buildForwardedHeaders(request) {
  const forwardedHeaders = { Accept: "application/zip" };

  const authorization = request.headers.get("authorization");
  const adminToken = request.headers.get("x-admin-token");
  if (authorization) forwardedHeaders.Authorization = authorization;
  if (adminToken) forwardedHeaders["X-Admin-Token"] = adminToken;

  if (request.method === "POST") {
    const formData = await request.formData();
    const idToken = String(formData.get("idToken") || "").trim();
    const postedAdminToken = String(formData.get("adminToken") || "").trim();

    if (idToken && !forwardedHeaders.Authorization) {
      forwardedHeaders.Authorization = idToken.toLowerCase().startsWith("bearer ")
        ? idToken
        : `Bearer ${idToken}`;
    }
    if (postedAdminToken && !forwardedHeaders["X-Admin-Token"]) {
      forwardedHeaders["X-Admin-Token"] = postedAdminToken;
    }
  }

  return forwardedHeaders;
}

async function proxyDownload(request, { params }) {
  const { projectId } = await params;
  const vpsUrl = process.env.NEXT_PUBLIC_VPS_API_URL || "http://187.77.30.158:8085";

  try {
    const forwardedHeaders = await buildForwardedHeaders(request);

    const response = await fetch(
      `${vpsUrl}/download/all/${encodeURIComponent(projectId)}`,
      { headers: forwardedHeaders },
    );

    if (!response.ok) {
      const contentType = response.headers.get("content-type") || "application/json";
      const body = await response.text();
      return new Response(body || JSON.stringify({ error: "Package not available" }), {
        status: response.status,
        headers: { "Content-Type": contentType },
      });
    }

    const contentLength = response.headers.get("content-length");
    const disposition = response.headers.get("content-disposition");
    const safeName = `${projectId}_material_completo.zip`.replace(/[^a-zA-Z0-9_\-.]/g, "_");

    return new Response(response.body, {
      status: 200,
      headers: {
        "Content-Type": "application/zip",
        "Content-Disposition": disposition || `attachment; filename="${safeName}"`,
        ...(contentLength && { "Content-Length": contentLength }),
        "Cache-Control": "no-cache",
      },
    });
  } catch (error) {
    Sentry.captureException(error, {
      tags: { route: "download_all_proxy" },
      extra: { projectId },
    });
    console.error("Full package download proxy error:", error);
    return new Response(JSON.stringify({ error: "Download failed" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}

export async function GET(request, context) {
  return proxyDownload(request, context);
}

export async function POST(request, context) {
  return proxyDownload(request, context);
}
