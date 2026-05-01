/**
 * API Route Proxy — Download images ZIP from VPS over HTTPS
 */
export async function GET(request, { params }) {
  const { project } = await params;
  const vpsUrl = process.env.NEXT_PUBLIC_VPS_API_URL || "http://100.99.207.113:8085";

  try {
    const response = await fetch(`${vpsUrl}/download/images/${encodeURIComponent(project)}`);

    if (!response.ok) {
      return new Response(JSON.stringify({ error: "Images not found" }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      });
    }

    const contentLength = response.headers.get("Content-Length");
    const safeName = `${project}_imagenes.zip`.replace(/[^a-zA-Z0-9_\-\.]/g, "_");

    return new Response(response.body, {
      status: 200,
      headers: {
        "Content-Type": "application/zip",
        "Content-Disposition": `attachment; filename="${safeName}"`,
        ...(contentLength && { "Content-Length": contentLength }),
        "Cache-Control": "no-cache",
      },
    });
  } catch (error) {
    console.error("Images download proxy error:", error);
    return new Response(JSON.stringify({ error: "Download failed" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}
