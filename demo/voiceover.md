# Bansho Demo Voiceover (ElevenLabs TTS)

## Settings
- **Voice:** Pick a calm, confident male or female voice (e.g. "Adam", "Rachel", or "Antoni")
- **Stability:** 0.50
- **Clarity + Similarity Enhancement:** 0.75
- **Style:** 0 (neutral — no dramatic flair)
- **Speed:** Slightly slow

## Script

Bansho. An enterprise-grade security gateway for the Model Context Protocol.

Right now, MCP servers are being deployed everywhere, exposing internal tools and databases directly to AI models. Most of them have zero authentication, no rate limiting, and no audit trails. That's a massive security risk.

Here's how Bansho solves this.

It sits as a proxy between your AI clients and your existing MCP servers—requiring zero code changes. 

Bansho enforces API key authentication, role-based tool authorization, and strict rate limits. Every single request and response is captured in a tamper-proof PostgreSQL audit log.

Let me show you the difference. I'm running the demo script now.

First, the before state. We have a vulnerable MCP server. A client connects without credentials and successfully calls a sensitive tool—deleting a customer record. No resistance. No logs.

Now, we route that same traffic through Bansho.

Watch the gates activate. A request with no API key? Instantly rejected with a 401 Unauthorized. 

A read-only user tries to call that sensitive delete tool? Blocked with a 403 Forbidden. 

A user spams a safe tool too fast? Rate-limited with a 429. 

Only the admin key succeeds. And behind the scenes, Bansho’s dashboard captures every single decision, latency metric, and payload for compliance.

Security, visibility, and control for your AI toolchain.

Built for the Microsoft AI Dev Days Hackathon twenty twenty-six. Thank you for watching.
