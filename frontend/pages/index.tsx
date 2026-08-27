import { useState } from "react";

export default function Home() {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState<any>(null);

  async function submit() {
    const res = await fetch("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, top_n: 7, platforms: ["tiktok", "instagram", "youtube"] }),
    });
    const data = await res.json();
    poll(data.job_id);
  }

  async function poll(id: string) {
    const res = await fetch(`/api/jobs/${id}`);
    const data = await res.json();
    setStatus(data);
    if (data.state === "running" || data.state === "queued") setTimeout(() => poll(id), 3000);
  }

  return (
    <main style={{ padding: 40, fontFamily: "sans-serif" }}>
      <h1>ClipForge</h1>
      <input
        placeholder="YouTube / Twitch URL"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        style={{ width: 400, padding: 8 }}
      />
      <button onClick={submit} style={{ marginLeft: 8, padding: "8px 16px" }}>Clip it</button>

      {status && (
        <section style={{ marginTop: 32 }}>
          <h3>Job: {status.state}</h3>
          {(status.moments || []).map((m: any, i: number) => (
            <div key={i} style={{ border: "1px solid #ddd", padding: 12, marginBottom: 8 }}>
              <strong>Score {m.score}</strong> — {m.hook}
              <div style={{ color: "#666" }}>{m.reason}</div>
              <div style={{ fontSize: 12 }}>{m.start}s – {m.end}s</div>
            </div>
          ))}
          {(status.publish_results || []).map((p: any, i: number) => (
            <div key={i} style={{ fontSize: 13, color: p.ok ? "green" : "red" }}>
              {p.platform}: {p.ok ? "published" : p.error}
            </div>
          ))}
          {status.error && <p style={{ color: "red" }}>{status.error}</p>}
        </section>
      )}
    </main>
  );
}
