/**
 * API Route Proxy — Download video from VPS over HTTPS
 * Solves mixed-content blocking (HTTPS Vercel → HTTP VPS)
 */
export async function GET(request, { params }) {
  const { project } = await params;
  const vpsUrl = process.env.NEXT_PUBLIC_VPS_API_URL || "http://100.99.207.113:8085";

  try {
    const response = await fetch(`${vpsUrl}/download/video/${encodeURIComponent(project)}`, {
      headers: { "Accept": "video/mp4" },
    });

    if (!response.ok) {
      return new Response(JSON.stringify({ error: "Video not found" }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      });
    }

    const contentLength = response.headers.get("Content-Length");
    const safeName = `${project}.mp4`.replace(/[^a-zA-Z0-9_\-\.]/g, "_");

    return new Response(response.body, {
      status: 200,
      headers: {
        "Content-Type": "video/mp4",
        "Content-Disposition": `attachment; filename="${safeName}"`,
        ...(contentLength && { "Content-Length": contentLength }),
        "Cache-Control": "no-cache",
      },
    });
  } catch (error) {
    console.error("Download proxy error:", error);
    return new Response(JSON.stringify({ error: "Download failed" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}
