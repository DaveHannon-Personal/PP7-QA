/**
 * Runtime API proxy — forwards all /api/* requests to the FastAPI backend.
 * Reads API_INTERNAL_URL at request time so Docker env vars work correctly.
 */

import { NextRequest, NextResponse } from "next/server";

const BACKEND = (process.env.API_INTERNAL_URL || "http://localhost:8000").replace(/\/$/, "");

async function proxy(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
    const { path } = await params;
    const url = `${BACKEND}/api/${path.join("/")}${req.nextUrl.search}`;

    const headers = new Headers(req.headers);
    headers.delete("host");

    const init: RequestInit = {
        method: req.method,
        headers,
        body: ["GET", "HEAD"].includes(req.method) ? undefined : req.body,
        // @ts-expect-error — Node fetch duplex requirement
        duplex: "half",
    };

    try {
        const res = await fetch(url, init);
        const body = await res.arrayBuffer();
        return new NextResponse(body, {
            status: res.status,
            headers: res.headers,
        });
    } catch (err) {
        console.error(`[proxy] ${req.method} ${url} failed:`, err);
        return NextResponse.json({ error: "Backend unreachable" }, { status: 502 });
    }
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
