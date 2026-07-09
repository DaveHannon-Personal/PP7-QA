import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

export const metadata: Metadata = {
    title: "PP7-QA — ProPresenter 7 Quality Assurance",
    description: "AI-powered compliance auditing for ProPresenter 7",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="en">
            <body style={{ display: "flex", minHeight: "100vh" }}>
                <Sidebar />
                <main style={{ flex: 1, overflow: "auto" }}>{children}</main>
            </body>
        </html>
    );
}
