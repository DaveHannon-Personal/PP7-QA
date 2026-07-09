import type { NextConfig } from "next";

const nextConfig: NextConfig = {
    output: "standalone",
    async rewrites() {
        // In development, proxy /api/* calls to the FastAPI backend
        const apiUrl = process.env.API_INTERNAL_URL || "http://localhost:8000";
        return [
            {
                source: "/api/:path*",
                destination: `${apiUrl}/api/:path*`,
            },
        ];
    },
};

export default nextConfig;
