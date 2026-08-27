import { useEffect, useState } from "react";
import { api, getToken, setToken, clearToken } from "../lib/api";

type JobStatus = {
  job_id: string;
  state: string;
  moments?: { score: number; hook: string; reason: string; start: number; end: number }[];
  publish_results?: { platform: string; ok: boolean; error?: string }[];
  error?: string;
};

export default function Home() {
  const [token, setTok] = useState<string | null>(null);
  const [handle, setHandle] = useState("");
  const [password, setPassword] = useState("");
  const [authErr, setAuthErr] = useState<string | null>(null);

  const [url, setUrl] = useState("");
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    setTok(getToken());
  }, []);

  async function doRegister() {
    setAuthErr(null);
    const d = await api.register(handle, password);
    if (d.access_token) {
      setToken(d.access_token);
      setTok(d.access_token);
    } else setAuthErr(d.detail || "register failed");
  }

  async function doLogin() {
    setAuthErr(null);
    const d = await api.login(handle, password);
    if (d.access_token) {
      setToken(d.access_token);
      setTok(d.access_token);
    } else setAuthErr(d.detail || "login failed");
  }

  async function doLogout() {
    await api.logout();
    clearToken();
    setTok(null);
  }

  async function submit() {
    setMsg(null);
    const d = await api.createJob(url, 7, ["tiktok", "instagram", "youtube"]);
    if (d.job_id) poll(d.job_id);
    else setMsg(d.detail || "could not start job");
  }

  async function poll(id: string) {
    const data = await api.getJob(id);
    setStatus(data);
    if (data.state === "running" || data.state === "queued")
      setTimeout(() => poll(id), 3000);
  }

  if (!token) {
    return (
      <main style={{ padding: 40, fontFamily: "sans-serif", maxWidth: 420 }}>
        <h1>ClipForge</h1>
        <input placeholder="handle" value={handle}
          onChange={(e) => setHandle(e.target.value)} style={inp} />
        <input placeholder="password" type="password" value={password}
          onChange={(e) => setPassword(e.target.value)} style={inp} />
        <div style={{ marginTop: 12 }}>
          <button onClick={doLogin} style={btn}>Login</button>
          <button onClick={doRegister} style={{ ...btn, marginLeft: 8 }}>Register</button>
        </div>
        {authErr && <p style={{ color: "red" }}>{authErr}</p>}
      </main>
    );
  }

  return (
    <main style={{ padding: 40, fontFamily: "sans-serif" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1>ClipForge</h1>
        <button onClick={doLogout} style={btn}>Logout</button>
      </div>

      <input placeholder="YouTube / Twitch URL" value={url}
        onChange={(e) => setUrl(e.target.value)}
        style={{ width: 400, padding: 8 }} />
      <button onClick={submit} style={{ marginLeft: 8, padding: "8px 16px" }}>Clip it</button>

      {msg && <p style={{ color: "red" }}>{msg}</p>}

      {status && (
        <section style={{ marginTop: 32 }}>
          <h3>Job: {status.state}</h3>
          {(status.moments || []).map((m, i) => (
            <div key={i} style={{ border: "1px solid #ddd", padding: 12, marginBottom: 8 }}>
              <strong>Score {m.score}</strong> — {m.hook}
              <div style={{ color: "#666" }}>{m.reason}</div>
              <div style={{ fontSize: 12 }}>{m.start}s – {m.end}s</div>
            </div>
          ))}
          {(status.publish_results || []).map((p, i) => (
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

const inp: React.CSSProperties = { display: "block", width: "100%", padding: 8, marginBottom: 8 };
const btn: React.CSSProperties = { padding: "8px 16px", cursor: "pointer" };
