import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { Activity, FileText, Languages, Lock, Mic, Play, Send } from "lucide-react";
import "./styles.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

function App() {
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [authMode, setAuthMode] = useState("signin");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [sourceLang, setSourceLang] = useState("en");
  const [targetLang, setTargetLang] = useState("ur");
  const [domain, setDomain] = useState("general");
  const [text, setText] = useState("");
  const [turns, setTurns] = useState([]);
  const [docText, setDocText] = useState("");
  const [analytics, setAnalytics] = useState(null);
  const [status, setStatus] = useState("");
  const socketRef = useRef(null);

  const headers = useMemo(() => ({ Authorization: `Bearer ${token}`, "Content-Type": "application/json" }), [token]);

  useEffect(() => {
    if (!token) return;
    fetch(`${API}/analytics`, { headers })
      .then((res) => res.json())
      .then(setAnalytics)
      .catch(() => {});
  }, [token, headers]);

  async function authenticate(event) {
    event.preventDefault();
    setStatus("Authenticating...");
    const res = await fetch(`${API}/auth/${authMode}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (!res.ok) {
      setStatus(data.detail || "Authentication failed");
      return;
    }
    localStorage.setItem("token", data.token);
    setToken(data.token);
    setStatus("Signed in");
  }

  async function translate() {
    if (!text.trim()) return;
    setStatus("Translating...");
    const res = await fetch(`${API}/translate`, {
      method: "POST",
      headers,
      body: JSON.stringify({ text, source_lang: sourceLang, target_lang: targetLang, domain, speak: true }),
    });
    const data = await res.json();
    if (!res.ok) {
      setStatus(data.detail || "Translation failed");
      return;
    }
    setTurns((items) => [data, ...items]);
    setText("");
    setStatus("Ready");
  }

  function connectConversation() {
    if (socketRef.current) return;
    const ws = new WebSocket(`${API.replace("http", "ws")}/ws/conversation?token=${token}`);
    ws.onopen = () => setStatus("Conversation mode connected");
    ws.onmessage = (event) => setTurns((items) => [JSON.parse(event.data), ...items]);
    ws.onclose = () => {
      socketRef.current = null;
      setStatus("Conversation mode disconnected");
    };
    socketRef.current = ws;
  }

  function sendRealtime() {
    if (!socketRef.current || !text.trim()) return;
    socketRef.current.send(JSON.stringify({ text, source_lang: sourceLang, target_lang: targetLang, domain }));
    setText("");
  }

  async function addDocument() {
    if (!docText.trim()) return;
    const res = await fetch(`${API}/documents`, {
      method: "POST",
      headers,
      body: JSON.stringify({ name: `${domain}-context`, text: docText }),
    });
    const data = await res.json();
    setStatus(res.ok ? `Context indexed: ${data.chunks} chunks` : data.detail || "Index failed");
    if (res.ok) setDocText("");
  }

  if (!token) {
    return (
      <main className="auth-shell">
        <form className="auth-panel" onSubmit={authenticate}>
          <div className="mark"><Lock size={26} /></div>
          <h1>Speech Translation</h1>
          <p>Offline-first multilingual speech-to-speech translation workspace.</p>
          <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username" />
          <input value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" type="password" />
          <div className="segmented">
            <button type="button" className={authMode === "signin" ? "active" : ""} onClick={() => setAuthMode("signin")}>Sign in</button>
            <button type="button" className={authMode === "signup" ? "active" : ""} onClick={() => setAuthMode("signup")}>Sign up</button>
          </div>
          <button className="primary">Continue</button>
          <span className="status">{status}</span>
        </form>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <aside>
        <h1><Languages size={24} /> Translator</h1>
        <label>Source</label>
        <select value={sourceLang} onChange={(e) => setSourceLang(e.target.value)}>
          <option value="en">English</option>
          <option value="ur">Urdu</option>
        </select>
        <label>Target</label>
        <select value={targetLang} onChange={(e) => setTargetLang(e.target.value)}>
          <option value="ur">Urdu</option>
          <option value="en">English</option>
        </select>
        <label>Domain</label>
        <select value={domain} onChange={(e) => setDomain(e.target.value)}>
          <option>general</option>
          <option>medical</option>
          <option>legal</option>
          <option>education</option>
          <option>travel</option>
        </select>
        <button onClick={() => { localStorage.removeItem("token"); setToken(""); }}>Sign out</button>
      </aside>

      <section className="workspace">
        <div className="composer">
          <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Speak-transcribed text or type a phrase..." />
          <div className="actions">
            <button onClick={translate}><Send size={18} /> Translate</button>
            <button onClick={connectConversation}><Mic size={18} /> Connect</button>
            <button onClick={sendRealtime}><Activity size={18} /> Send live</button>
          </div>
          <span className="status">{status}</span>
        </div>

        <div className="grid">
          <section className="panel">
            <h2>Conversation</h2>
            {turns.map((turn, index) => (
              <article className="turn" key={index}>
                <small>{turn.emotion}</small>
                <p>{turn.source_text}</p>
                <strong>{turn.translated_text}</strong>
                {turn.audio_url && <audio controls src={`${API}${turn.audio_url}`} />}
              </article>
            ))}
          </section>

          <section className="panel">
            <h2><FileText size={18} /> RAG Context</h2>
            <textarea value={docText} onChange={(e) => setDocText(e.target.value)} placeholder="Paste domain notes, glossary, policy, or medical context..." />
            <button onClick={addDocument}><Play size={18} /> Index context</button>
            <h2><Activity size={18} /> Analytics</h2>
            <p>Total translations: {analytics?.total_translations ?? 0}</p>
            {(analytics?.language_pairs || []).map((pair) => <p key={pair.pair}>{pair.pair}: {pair.count}</p>)}
          </section>
        </div>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
