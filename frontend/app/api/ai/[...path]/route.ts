import { proxyRequest } from "@/lib/api/proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type Context = { params: Promise<{ path: string[] }> };

export async function GET(request: Request, context: Context) { return proxyRequest(request, context, "ai"); }
export async function POST(request: Request, context: Context) { return proxyRequest(request, context, "ai"); }
export async function PUT(request: Request, context: Context) { return proxyRequest(request, context, "ai"); }
export async function PATCH(request: Request, context: Context) { return proxyRequest(request, context, "ai"); }
export async function DELETE(request: Request, context: Context) { return proxyRequest(request, context, "ai"); }
