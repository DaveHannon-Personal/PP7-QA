/**
 * AI Chat page — streaming chat with Ollama for rule creation and Q&A.
 * When the AI responds with a JSON rule block, a "Save Rule" button appears.
 */
"use client";

import { useEffect, useRef, useState } from "react";
import { rulesApi, type RuleCreate } from "@/lib/api";
import { Send, Bot, User, Plus, Loader2 } from "lucide-react";

interface Message {
    role: "user" | "assistant";
    content: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

export default function ChatPage() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [streaming, setStreaming] = useState(false);
    const [pendingRule, setPendingRule] = useState<RuleCreate | null>(null);
    const [savedRule, setSavedRule] = useState(false);
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    async function sendMessage() {
        const text = input.trim();
        if (!text || streaming) return;
        setInput("");
        setPendingRule(null);
        setSavedRule(false);

        const newMessages: Message[] = [...messages, { role: "user", content: text }];
        setMessages(newMessages);
        setStreaming(true);

        const assistantMsg: Message = { role: "assistant", content: "" };
        setMessages([...newMessages, assistantMsg]);

        try {
            const res = await fetch(`${API_URL}/api/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ messages: newMessages, stream: true }),
            });

            if (!res.ok) throw new Error(`API error ${res.status}`);

            const reader = res.body?.getReader();
            const decoder = new TextDecoder();
            let fullContent = "";

            if (reader) {
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    const text = decoder.decode(value);
                    const lines = text.split("\n");
                    for (const line of lines) {
                        if (!line.startsWith("data: ") || line === "data: [DONE]") continue;
                        try {
                            const data = JSON.parse(line.slice(6));
                            if (data.content) {
                                fullContent += data.content;
                                setMessages((prev) => [
                                    ...prev.slice(0, -1),
                                    { role: "assistant", content: fullContent },
                                ]);
                            }
                        } catch { }
                    }
                }
            }

            // Check for embedded rule JSON
            const ruleMatch = fullContent.match(/```json\s*([\s\S]*?)\s*```/);
            if (ruleMatch) {
                try {
                    const parsed = JSON.parse(ruleMatch[1]);
                    if (parsed.action === "create_rule" && parsed.rule) {
                        setPendingRule(parsed.rule as RuleCreate);
                    }
                } catch { }
            }
        } catch (e) {
            setMessages((prev) => [
                ...prev.slice(0, -1),
                { role: "assistant", content: `Error: ${e}` },
            ]);
        }

        setStreaming(false);
    }

    async function saveRule() {
        if (!pendingRule) return;
        try {
            await rulesApi.create(pendingRule);
            setSavedRule(true);
            setPendingRule(null);
        } catch (e) {
            alert("Failed to save rule: " + e);
        }
    }

    return (
        <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
            {/* Header */}
            <div style={{ padding: "20px 28px 14px", borderBottom: "1px solid var(--border)", background: "var(--surface)" }}>
                <h1 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>AI Chat</h1>
                <p style={{ fontSize: 13, color: "var(--text-muted)", margin: "4px 0 0" }}>
                    Describe a compliance rule in plain English and the AI will create it for you
                </p>
            </div>

            {/* Messages */}
            <div style={{ flex: 1, overflowY: "auto", padding: "20px 28px" }}>
                {messages.length === 0 && <WelcomeHints onSend={(hint) => { setInput(hint); }} />}

                {messages.map((msg, i) => (
                    <MessageBubble key={i} msg={msg} />
                ))}

                {/* Save rule CTA */}
                {pendingRule && !savedRule && (
                    <div style={{ background: "rgba(99,102,241,0.1)", border: "1px solid var(--accent)", borderRadius: 10, padding: "14px 18px", marginTop: 12, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 14 }}>
                        <div>
                            <div style={{ fontWeight: 600, fontSize: 14 }}>Rule detected: "{pendingRule.name}"</div>
                            <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 3 }}>
                                Target: {pendingRule.target} · Severity: {pendingRule.severity}
                            </div>
                        </div>
                        <button onClick={saveRule} style={{ display: "flex", alignItems: "center", gap: 6, background: "var(--accent)", color: "#fff", border: "none", borderRadius: 8, padding: "8px 14px", cursor: "pointer", fontWeight: 600, fontSize: 13, flexShrink: 0 }}>
                            <Plus size={14} /> Save Rule
                        </button>
                    </div>
                )}

                {savedRule && (
                    <div style={{ fontSize: 13, color: "var(--success)", marginTop: 8 }}>
                        ✓ Rule saved! View it on the Rules page.
                    </div>
                )}

                {streaming && (
                    <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-muted)", fontSize: 13, marginTop: 8 }}>
                        <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} />
                        AI is thinking…
                    </div>
                )}

                <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div style={{ padding: "14px 28px", borderTop: "1px solid var(--border)", background: "var(--surface)" }}>
                <div style={{ display: "flex", gap: 10, alignItems: "flex-end" }}>
                    <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                        placeholder='Ask the AI to create a rule, e.g. "All presentations must use the Main Look"'
                        rows={2}
                        style={{ flex: 1, background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: 10, padding: "10px 14px", color: "var(--text)", fontSize: 14, resize: "none", outline: "none", lineHeight: 1.5 }}
                    />
                    <button onClick={sendMessage} disabled={streaming || !input.trim()} style={{ background: "var(--accent)", border: "none", borderRadius: 10, padding: "10px 14px", cursor: "pointer", color: "#fff", opacity: streaming || !input.trim() ? 0.5 : 1 }}>
                        <Send size={16} />
                    </button>
                </div>
                <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 6 }}>Enter to send · Shift+Enter for new line</div>
            </div>
        </div>
    );
}

function MessageBubble({ msg }: { msg: Message }) {
    const isUser = msg.role === "user";
    return (
        <div style={{ display: "flex", gap: 10, marginBottom: 16, flexDirection: isUser ? "row-reverse" : "row" }}>
            <div style={{ width: 28, height: 28, borderRadius: "50%", background: isUser ? "var(--accent)" : "var(--surface-2)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                {isUser ? <User size={14} /> : <Bot size={14} />}
            </div>
            <div style={{
                background: isUser ? "var(--accent)" : "var(--surface)",
                border: isUser ? "none" : "1px solid var(--border)",
                borderRadius: 12,
                padding: "10px 14px",
                maxWidth: "75%",
                fontSize: 14,
                lineHeight: 1.6,
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
            }}>
                {msg.content}
            </div>
        </div>
    );
}

function WelcomeHints({ onSend }: { onSend: (t: string) => void }) {
    const hints = [
        "All presentations must use the Look named 'Main'",
        "Every slide should have a theme assigned",
        "Presentations must not have empty names",
        "All props should have their auto-clear timer enabled",
    ];
    return (
        <div style={{ marginBottom: 24 }}>
            <div style={{ textAlign: "center", marginBottom: 20 }}>
                <Bot size={40} color="var(--accent)" style={{ marginBottom: 8 }} />
                <div style={{ fontWeight: 600, fontSize: 16 }}>PP7-QA Assistant</div>
                <div style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 4 }}>
                    Describe a compliance rule and I&apos;ll turn it into a QA check
                </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                {hints.map((h) => (
                    <button key={h} onClick={() => onSend(h)} style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, padding: "12px 16px", cursor: "pointer", textAlign: "left", color: "var(--text)", fontSize: 13, lineHeight: 1.4 }}>
                        &ldquo;{h}&rdquo;
                    </button>
                ))}
            </div>
        </div>
    );
}
