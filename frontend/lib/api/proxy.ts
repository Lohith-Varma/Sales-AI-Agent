const hopByHopHeaders = new Set(["connection", "host", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailer", "transfer-encoding", "upgrade"]);

export async function proxyRequest(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
  service: "core" | "ai",
) {
  const { path } = await context.params;
  const defaultUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
  const base = service === "core"
    ? process.env.CORE_API_URL ?? process.env.NEXT_PUBLIC_CORE_API_URL ?? defaultUrl
    : process.env.AI_API_URL ?? process.env.NEXT_PUBLIC_AI_API_URL ?? defaultUrl;


  const incoming = new URL(request.url);
  const normalizedBase = base.endsWith("/") ? base : `${base}/`;
  const target = new URL(path.map(encodeURIComponent).join("/"), normalizedBase);
  target.search = incoming.search;

  const headers = new Headers();
  request.headers.forEach((value, key) => { if (!hopByHopHeaders.has(key.toLowerCase()) && key.toLowerCase() !== "content-length") headers.set(key, value); });

  const hasBody = !["GET", "HEAD"].includes(request.method);
  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body: hasBody ? await request.arrayBuffer() : undefined,
      cache: "no-store",
      redirect: "manual",
    });
    const responseHeaders = new Headers();
    upstream.headers.forEach((value, key) => { if (!hopByHopHeaders.has(key.toLowerCase())) responseHeaders.set(key, value); });
    return new Response(upstream.body, { status: upstream.status, statusText: upstream.statusText, headers: responseHeaders });
  } catch {
    return Response.json({ code: "service_unavailable", message: `The ${service} service could not be reached.`, retryable: true }, { status: 503 });
  }
}
