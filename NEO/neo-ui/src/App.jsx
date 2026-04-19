import { useState, useEffect, useRef, useCallback } from "react";

// ─── Sound Effects ────────────────────────────────────────────────────────────
const AudioCtx = typeof window !== "undefined" ? new (window.AudioContext || window.webkitAudioContext)() : null;

function playTone(freq = 440, type = "sine", duration = 0.08, vol = 0.08) {
  if (!AudioCtx) return;
  try {
    const o = AudioCtx.createOscillator();
    const g = AudioCtx.createGain();
    o.connect(g); g.connect(AudioCtx.destination);
    o.type = type; o.frequency.setValueAtTime(freq, AudioCtx.currentTime);
    g.gain.setValueAtTime(vol, AudioCtx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.001, AudioCtx.currentTime + duration);
    o.start(); o.stop(AudioCtx.currentTime + duration);
  } catch {}
}
const sfx = {
  keyClick: () => playTone(800, "square", 0.04, 0.04),
  send:     () => { playTone(600, "sine", 0.1, 0.1); setTimeout(() => playTone(900, "sine", 0.08, 0.08), 80); },
  notify:   () => { playTone(440, "sine", 0.15, 0.1); setTimeout(() => playTone(660, "sine", 0.15, 0.1), 120); },
  connect:  () => [300, 450, 600, 750].forEach((f, i) => setTimeout(() => playTone(f, "sine", 0.1, 0.1), i * 80)),
  error:    () => { playTone(200, "sawtooth", 0.2, 0.12); setTimeout(() => playTone(150, "sawtooth", 0.2, 0.12), 150); },
};

// ─── CSS Injection ────────────────────────────────────────────────────────────
const GLOBAL_CSS = `
  @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@400;700;900&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --neon:   #00ffcc;
    --neon2:  #00aaff;
    --neon3:  #aa00ff;
    --red:    #ff003c;
    --bg:     #020b10;
    --panel:  rgba(0,255,204,0.03);
    --border: rgba(0,255,204,0.15);
    --text:   #a0e8cc;
    --dim:    #3a6a58;
  }

  html, body, #root { height: 100%; background: var(--bg); font-family: 'Share Tech Mono', monospace; color: var(--text); overflow: hidden; }

  ::-webkit-scrollbar { width: 4px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--neon); border-radius: 2px; }

  .orbitron { font-family: 'Orbitron', monospace; }

  /* Scanlines */
  .scanlines::before {
    content: ''; position: absolute; inset: 0; pointer-events: none; z-index: 9999;
    background: repeating-linear-gradient(to bottom, transparent 0px, transparent 3px, rgba(0,0,0,0.08) 3px, rgba(0,0,0,0.08) 4px);
  }

  /* Glow text */
  .glow-green { text-shadow: 0 0 8px #00ffcc, 0 0 20px #00ffcc66; }
  .glow-blue  { text-shadow: 0 0 8px #00aaff, 0 0 20px #00aaff66; }
  .glow-red   { text-shadow: 0 0 8px #ff003c, 0 0 20px #ff003c66; }
  .glow-purple{ text-shadow: 0 0 8px #aa00ff, 0 0 20px #aa00ff66; }

  /* Glow box */
  .glow-box-green { box-shadow: 0 0 10px #00ffcc33, 0 0 30px #00ffcc11, inset 0 0 10px #00ffcc08; }
  .glow-box-blue  { box-shadow: 0 0 10px #00aaff33, 0 0 30px #00aaff11, inset 0 0 10px #00aaff08; }
  .glow-box-red   { box-shadow: 0 0 10px #ff003c33, 0 0 30px #ff003c11, inset 0 0 10px #ff003c08; }
  .glow-box-purple{ box-shadow: 0 0 10px #aa00ff33, 0 0 30px #aa00ff11, inset 0 0 10px #aa00ff08; }

  /* Panel glass */
  .glass {
    background: var(--panel);
    backdrop-filter: blur(12px);
    border: 1px solid var(--border);
  }

  /* Blink cursor */
  @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
  .cursor-blink { animation: blink 1s infinite; }

  /* Pulse */
  @keyframes pulse-neon { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.6;transform:scale(0.95)} }
  .pulse { animation: pulse-neon 2s infinite; }

  /* Spin */
  @keyframes spin { to { transform: rotate(360deg); } }
  .spin { animation: spin 1s linear infinite; }

  /* Slide in */
  @keyframes slideIn { from { transform: translateX(120%); opacity:0; } to { transform: translateX(0); opacity:1; } }
  .slide-in { animation: slideIn 0.4s cubic-bezier(0.22,1,0.36,1); }

  /* Fade in */
  @keyframes fadeIn { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
  .fade-in { animation: fadeIn 0.3s ease; }

  /* Matrix rain */
  @keyframes matrixFall { from { transform: translateY(-100%); opacity:1; } to { transform: translateY(100vh); opacity:0; } }

  /* Glitch */
  @keyframes glitch {
    0%,100% { clip-path: none; transform: none; }
    92% { clip-path: polygon(0 20%, 100% 20%, 100% 25%, 0 25%); transform: translate(-3px,0); }
    94% { clip-path: polygon(0 60%, 100% 60%, 100% 65%, 0 65%); transform: translate(3px,0); }
    96% { clip-path: none; transform: none; }
  }
  .glitch-hover:hover { animation: glitch 0.5s steps(1); }

  /* Progress bar shimmer */
  @keyframes shimmer { from{background-position:-200% 0} to{background-position:200% 0} }

  /* Corner decorators */
  .corner-tl::before, .corner-br::after {
    content: ''; position: absolute; width: 12px; height: 12px; border-color: var(--neon);
  }
  .corner-tl::before { top:0;left:0; border-top:2px solid; border-left:2px solid; }
  .corner-br::after  { bottom:0;right:0; border-bottom:2px solid; border-right:2px solid; }

  /* Button */
  .neo-btn {
    position: relative; cursor: pointer; overflow: hidden;
    font-family: 'Orbitron', monospace; font-size: 11px; letter-spacing: 2px; font-weight: 700;
    padding: 8px 20px; border: 1px solid var(--neon); color: var(--neon);
    background: rgba(0,255,204,0.05);
    transition: all 0.2s;
    clip-path: polygon(8px 0%, 100% 0%, calc(100% - 8px) 100%, 0% 100%);
  }
  .neo-btn::before {
    content: ''; position: absolute; inset:0;
    background: var(--neon); opacity: 0; transition: opacity 0.2s;
  }
  .neo-btn:hover { color: #000; box-shadow: 0 0 20px var(--neon); }
  .neo-btn:hover::before { opacity:1; }
  .neo-btn span { position: relative; z-index:1; }
  .neo-btn:active { transform: scale(0.97); }

  /* Input */
  .neo-input {
    background: rgba(0,255,204,0.04); border: 1px solid rgba(0,255,204,0.3);
    color: var(--neon); caret-color: var(--neon); outline: none;
    font-family: 'Share Tech Mono', monospace; font-size: 13px;
    padding: 10px 14px; width: 100%;
    transition: border-color 0.2s, box-shadow 0.2s;
  }
  .neo-input:focus { border-color: var(--neon); box-shadow: 0 0 12px rgba(0,255,204,0.3); }
  .neo-input::placeholder { color: var(--dim); }

  /* Sidebar item */
  .nav-item {
    position: relative; cursor: pointer; padding: 12px 16px;
    font-family: 'Orbitron', monospace; font-size: 10px; letter-spacing: 2px; font-weight: 700;
    color: var(--dim); transition: all 0.2s; border-left: 2px solid transparent;
    display: flex; align-items: center; gap: 10px;
  }
  .nav-item:hover { color: var(--neon); border-left-color: var(--neon); background: rgba(0,255,204,0.05); }
  .nav-item.active { color: var(--neon); border-left-color: var(--neon); background: rgba(0,255,204,0.08); text-shadow: 0 0 8px var(--neon); }
  .nav-item.active::after { content: '◄'; position: absolute; right: 12px; font-size: 8px; color: var(--neon); }

  /* Bar chart */
  .bar-fill { transition: width 1s cubic-bezier(0.22,1,0.36,1); }

  /* Log entry */
  .log-entry { animation: fadeIn 0.2s ease; }

  /* Notification */
  .notif-enter { animation: slideIn 0.4s cubic-bezier(0.22,1,0.36,1); }

  /* Hex grid bg decoration */
  .hex-bg {
    position: fixed; inset:0; pointer-events:none; z-index:0; overflow:hidden;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='60' height='52'%3E%3Cpolygon points='30,2 58,17 58,47 30,52 2,47 2,17' fill='none' stroke='%2300ffcc08' stroke-width='1'/%3E%3C/svg%3E");
    background-size: 60px 52px;
  }
`;

// ─── Utility ──────────────────────────────────────────────────────────────────
const timestamp = () => new Date().toLocaleTimeString("en-US", { hour12: false });
const randBetween = (a, b) => Math.floor(Math.random() * (b - a + 1)) + a;

const LOG_TYPES = {
  INFO:    { color: "#00ffcc", prefix: "INFO" },
  WARN:    { color: "#ffaa00", prefix: "WARN" },
  ERROR:   { color: "#ff003c", prefix: "ERRR" },
  SYS:     { color: "#aa00ff", prefix: "SYS " },
  DATA:    { color: "#00aaff", prefix: "DATA" },
  SUCCESS: { color: "#00ff88", prefix: "SUCC" },
};

// ─── Typing Effect Hook ───────────────────────────────────────────────────────
function useTypingEffect(text, speed = 18) {
  const [displayed, setDisplayed] = useState("");
  const [done, setDone] = useState(false);
  useEffect(() => {
    setDisplayed(""); setDone(false);
    if (!text) return;
    let i = 0;
    const iv = setInterval(() => {
      i++;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) { clearInterval(iv); setDone(true); }
    }, speed);
    return () => clearInterval(iv);
  }, [text, speed]);
  return { displayed, done };
}

// ─── Matrix Rain ──────────────────────────────────────────────────────────────
function MatrixRain() {
  const canvasRef = useRef(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
    const cols = Math.floor(canvas.width / 16);
    const drops = Array(cols).fill(1);
    const chars = "01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモ";
    const draw = () => {
      ctx.fillStyle = "rgba(2,11,16,0.05)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = "#00ffcc22";
      ctx.font = "12px Share Tech Mono";
      drops.forEach((y, i) => {
        const ch = chars[Math.floor(Math.random() * chars.length)];
        ctx.fillStyle = i % 3 === 0 ? "#00ffcc44" : "#00ffcc11";
        ctx.fillText(ch, i * 16, y * 16);
        if (y * 16 > canvas.height && Math.random() > 0.975) drops[i] = 0;
        drops[i]++;
      });
    };
    const iv = setInterval(draw, 50);
    return () => clearInterval(iv);
  }, []);
  return <canvas ref={canvasRef} style={{ position:"fixed", inset:0, width:"100%", height:"100%", opacity:0.12, pointerEvents:"none", zIndex:0 }} />;
}

// ─── Notification System ──────────────────────────────────────────────────────
let _notifId = 0;
function NotificationCenter({ notifs, dismiss }) {
  return (
    <div style={{ position:"fixed", top:72, right:16, zIndex:9000, display:"flex", flexDirection:"column", gap:8, maxWidth:320 }}>
      {notifs.map(n => (
        <div key={n.id} className="notif-enter glass corner-tl corner-br" onClick={() => dismiss(n.id)}
          style={{ padding:"12px 16px", borderColor: n.color, boxShadow:`0 0 20px ${n.color}44`, cursor:"pointer", position:"relative" }}>
          <div style={{ fontFamily:"Orbitron,monospace", fontSize:9, letterSpacing:2, color: n.color, marginBottom:4 }}>
            {n.type} — {n.time}
          </div>
          <div style={{ fontSize:12, color:"#ccc" }}>{n.msg}</div>
          <div style={{ position:"absolute", top:8, right:10, fontSize:10, color: n.color, opacity:0.5 }}>×</div>
        </div>
      ))}
    </div>
  );
}

// ─── Status Indicator ─────────────────────────────────────────────────────────
function StatusDot({ online, label }) {
  return (
    <div style={{ display:"flex", alignItems:"center", gap:6 }}>
      <div style={{
        width:8, height:8, borderRadius:"50%",
        background: online ? "#00ffcc" : "#ff003c",
        boxShadow: online ? "0 0 8px #00ffcc, 0 0 16px #00ffcc88" : "0 0 8px #ff003c",
        animation: online ? "pulse-neon 2s infinite" : "none",
      }} />
      <span style={{ fontFamily:"Orbitron,monospace", fontSize:9, letterSpacing:2, color: online ? "#00ffcc" : "#ff003c" }}>
        {label}: {online ? "ONLINE" : "OFFLINE"}
      </span>
    </div>
  );
}

// ─── Header ───────────────────────────────────────────────────────────────────
function Header({ wsStatus, sysOnline }) {
  const [tick, setTick] = useState(0);
  useEffect(() => { const iv = setInterval(() => setTick(t => t + 1), 1000); return () => clearInterval(iv); }, []);
  const now = new Date();

  return (
    <header className="glass" style={{
      position:"fixed", top:0, left:0, right:0, height:56, zIndex:1000,
      display:"flex", alignItems:"center", justifyContent:"space-between",
      padding:"0 20px", borderBottom:"1px solid rgba(0,255,204,0.2)",
      boxShadow:"0 0 30px rgba(0,255,204,0.1)",
    }}>
      {/* Left: Logo */}
      <div style={{ display:"flex", alignItems:"center", gap:12 }}>
        <div style={{ width:32, height:32, position:"relative" }}>
          <svg viewBox="0 0 32 32" width="32" height="32">
            <polygon points="16,2 30,10 30,22 16,30 2,22 2,10" fill="none" stroke="#00ffcc" strokeWidth="1.5"
              style={{ filter:"drop-shadow(0 0 6px #00ffcc)" }} />
            <polygon points="16,8 24,13 24,21 16,26 8,21 8,13" fill="rgba(0,255,204,0.15)" stroke="#00ffcc88" strokeWidth="1" />
            <circle cx="16" cy="16" r="3" fill="#00ffcc" style={{ filter:"drop-shadow(0 0 4px #00ffcc)" }} />
          </svg>
        </div>
        <div>
          <div className="orbitron glow-green" style={{ fontSize:16, fontWeight:900, letterSpacing:4 }}>NEO AI SYSTEM</div>
          <div style={{ fontSize:9, letterSpacing:3, color:"#3a6a58" }}>v3.0 — CLASSIFIED</div>
        </div>
      </div>

      {/* Center: Status */}
      <div style={{ display:"flex", gap:20, alignItems:"center" }}>
        <StatusDot online={sysOnline} label="SYSTEM" />
        <StatusDot online={wsStatus === "CONNECTED"} label="WS" />
      </div>

      {/* Right: Clock */}
      <div style={{ textAlign:"right" }}>
        <div className="orbitron glow-green" style={{ fontSize:18, fontWeight:700, letterSpacing:3 }}>
          {now.toLocaleTimeString("en-US", { hour12:false })}
        </div>
        <div style={{ fontSize:9, letterSpacing:2, color:"#3a6a58" }}>
          {now.toLocaleDateString("en-US", { weekday:"short", month:"short", day:"2-digit", year:"numeric" }).toUpperCase()}
        </div>
      </div>
    </header>
  );
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────
const NAV = [
  { id:"dashboard",  icon:"⬡", label:"DASHBOARD" },
  { id:"logs",       icon:"◈", label:"LOGS" },
  { id:"chat",       icon:"◉", label:"AI CHAT" },
  { id:"monitor",    icon:"▣", label:"MONITOR" },
  { id:"settings",   icon:"⚙", label:"SETTINGS" },
];

function Sidebar({ active, setActive }) {
  return (
    <aside className="glass" style={{
      position:"fixed", left:0, top:56, bottom:0, width:180, zIndex:900,
      borderRight:"1px solid rgba(0,255,204,0.15)", display:"flex", flexDirection:"column",
      paddingTop:16,
    }}>
      <div style={{ padding:"0 16px 16px", borderBottom:"1px solid rgba(0,255,204,0.1)" }}>
        <div style={{ fontSize:9, letterSpacing:3, color:"#3a6a58" }}>NAVIGATION</div>
      </div>
      <nav style={{ flex:1, paddingTop:8 }}>
        {NAV.map(n => (
          <div key={n.id} className={`nav-item glitch-hover ${active === n.id ? "active" : ""}`}
            onClick={() => { setActive(n.id); sfx.keyClick(); }}>
            <span style={{ fontSize:14 }}>{n.icon}</span>
            <span>{n.label}</span>
          </div>
        ))}
      </nav>
      {/* Bottom decoration */}
      <div style={{ padding:16, borderTop:"1px solid rgba(0,255,204,0.1)" }}>
        <div style={{ fontSize:9, letterSpacing:1, color:"#3a6a58", lineHeight:1.6 }}>
          CORE: ALPHA-7<br/>
          NODE: 0x4E454F<br/>
          BUILD: 20260407
        </div>
      </div>
    </aside>
  );
}

// ─── Log Panel ────────────────────────────────────────────────────────────────
function LogPanel({ logs }) {
  const bottomRef = useRef(null);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior:"smooth" }); }, [logs]);

  return (
    <div className="glass glow-box-green corner-tl corner-br" style={{
      position:"relative", height:"100%", display:"flex", flexDirection:"column", overflow:"hidden",
    }}>
      <div style={{ padding:"10px 14px", borderBottom:"1px solid rgba(0,255,204,0.15)", display:"flex", alignItems:"center", gap:8 }}>
        <div style={{ width:6, height:6, borderRadius:"50%", background:"#00ffcc", boxShadow:"0 0 6px #00ffcc" }} className="pulse" />
        <span className="orbitron glow-green" style={{ fontSize:10, letterSpacing:3 }}>SYSTEM LOG</span>
        <span style={{ marginLeft:"auto", fontSize:9, color:"#3a6a58" }}>{logs.length}/50 ENTRIES</span>
      </div>
      <div style={{ flex:1, overflowY:"auto", padding:"8px 4px" }}>
        {logs.map((entry, i) => {
          const t = LOG_TYPES[entry.type] || LOG_TYPES.INFO;
          return (
            <div key={entry.id} className="log-entry" style={{ display:"flex", gap:8, padding:"3px 10px", fontSize:11, lineHeight:1.5, fontFamily:"Share Tech Mono,monospace" }}>
              <span style={{ color:"#3a6a58", flexShrink:0 }}>{entry.time}</span>
              <span style={{ color: t.color, flexShrink:0, textShadow:`0 0 6px ${t.color}` }}>[{t.prefix}]</span>
              <span style={{ color:"#88c4aa" }}>{entry.msg}</span>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

// ─── Chat Interface ───────────────────────────────────────────────────────────
const AI_RESPONSES = [
  "Analyzing neural pathways… quantum coherence at 94.7%. All subsystems nominal.",
  "Threat matrix updated. 3 anomalous signatures detected in sector 7. Initiating countermeasures.",
  "Memory allocation optimized. Freed 2.4TB across distributed nodes. Running defragmentation sequence.",
  "Biometric scan complete. Access granted. Welcome back, Commander. Auth token: NEO-7X-ALPHA.",
  "Deep scan initiated. Processing 847 terabytes of encrypted data through quantum filters.",
  "Firewall breach attempt neutralized at 03:14:22 UTC. Origin: 194.67.x.x. Blacklisted.",
  "System diagnostics: all 32 cores operating at peak efficiency. Thermal envelope: 67°C.",
  "Quantum encryption layer upgraded to AES-4096. Key rotation scheduled every 180 seconds.",
  "Command acknowledged. Executing protocol SHADOW-RUN. ETA: 4.2 seconds.",
  "Neural net recalibration complete. Prediction accuracy improved by 12.4%. Epoch 2847/∞.",
];

function ChatBubble({ msg }) {
  const { displayed, done } = useTypingEffect(msg.isAI ? msg.text : null, 15);
  return (
    <div className="fade-in" style={{ display:"flex", flexDirection:"column", alignItems: msg.isAI ? "flex-start" : "flex-end", marginBottom:12 }}>
      <div style={{ fontSize:9, letterSpacing:2, color:"#3a6a58", marginBottom:4 }}>
        {msg.isAI ? "◉ NEO-AI" : "▷ YOU"} — {msg.time}
      </div>
      <div style={{
        maxWidth:"80%", padding:"10px 14px", fontSize:12, lineHeight:1.6,
        background: msg.isAI ? "rgba(0,255,204,0.05)" : "rgba(0,170,255,0.07)",
        border: `1px solid ${msg.isAI ? "rgba(0,255,204,0.3)" : "rgba(0,170,255,0.3)"}`,
        color: msg.isAI ? "#a0e8cc" : "#a0ccff",
        boxShadow: msg.isAI ? "0 0 10px rgba(0,255,204,0.1)" : "0 0 10px rgba(0,170,255,0.1)",
        clipPath: msg.isAI ? "polygon(0 0,100% 0,100% 100%,8px 100%)" : "polygon(0 0,100% 0,calc(100% - 8px) 100%,0 100%)",
      }}>
        {msg.isAI ? displayed : msg.text}
        {msg.isAI && !done && <span className="cursor-blink" style={{ color:"#00ffcc" }}>█</span>}
      </div>
    </div>
  );
}

function ChatPanel({ sendWS }) {
  const [messages, setMessages] = useState([
    { id:0, isAI:true, text:"NEO AI SYSTEM v3.0 initialized. All neural cores online. How may I assist, Commander?", time:timestamp() },
  ]);
  const [input, setInput] = useState("");
  const [history, setHistory] = useState([]);
  const [histIdx, setHistIdx] = useState(-1);
  const [thinking, setThinking] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior:"smooth" }); }, [messages, thinking]);

  const send = () => {
    if (!input.trim()) return;
    const txt = input.trim();
    sfx.send();
    setMessages(m => [...m, { id: Date.now(), isAI:false, text:txt, time:timestamp() }]);
    setHistory(h => [txt, ...h]);
    setHistIdx(-1);
    setInput("");
    sendWS?.(txt);
    setThinking(true);
    const streamResponse = (fullText) => {
  let i = 0;
  const id = Date.now();

  setMessages(m => [...m, { id, isAI: true, text: "", time: timestamp() }]);

  const interval = setInterval(() => {
    i += randBetween(2, 5);

    setMessages(m =>
      m.map(msg =>
        msg.id === id
          ? { ...msg, text: fullText.slice(0, i) }
          : msg
      )
    );

    if (i >= fullText.length) {
      clearInterval(interval);
      setThinking(false);
    }
  }, 30 + Math.random() * 40);
  };
  };

  const onKey = (e) => {
    if (e.key === "Enter") { send(); return; }
    if (e.key === "ArrowUp") {
      const i = Math.min(histIdx + 1, history.length - 1);
      setHistIdx(i); setInput(history[i] || "");
      e.preventDefault();
    }
    if (e.key === "ArrowDown") {
      const i = Math.max(histIdx - 1, -1);
      setHistIdx(i); setInput(i === -1 ? "" : history[i]);
      e.preventDefault();
    }
    sfx.keyClick();
  };

  return (
    <div className="glass glow-box-blue corner-tl corner-br" style={{
      position:"relative", height:"100%", display:"flex", flexDirection:"column", overflow:"hidden",
    }}>
   ))
      <div style={{ padding:"10px 14px", borderBottom:"1px solid rgba(0,170,255,0.2)", display:"flex", alignItems:"center", gap:8 }}>
        <div style={{ width:6, height:6, borderRadius:"50%", background:"#00aaff", boxShadow:"0 0 6px #00aaff" }} className="pulse" />
        <span className="orbitron glow-blue" style={{ fontSize:10, letterSpacing:3 }}>AI INTERFACE</span>
      </div>
      <div style={{ flex:1, overflowY:"auto", padding:12 }}>
        {messages.map(m => <ChatBubble key={m.id} msg={m} />)}
        {thinking && (
          <div className="fade-in" style={{ display:"flex", alignItems:"center", gap:8, padding:"8px 0", color:"#00ffcc88", fontSize:12 }}>
            <div className="spin" style={{ width:12, height:12, border:"2px solid #00ffcc33", borderTopColor:"#00ffcc", borderRadius:"50%" }} />
            Processing neural query…
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div style={{ padding:12, borderTop:"1px solid rgba(0,170,255,0.2)", display:"flex", gap:8 }}>
        <input className="neo-input" value={input} onChange={e => setInput(e.target.value)} onKeyDown={onKey}
          placeholder="ENTER COMMAND › ↑↓ HISTORY" style={{ borderColor:"rgba(0,170,255,0.4)" }} />
        <button className="neo-btn" onClick={send} style={{ borderColor:"#00aaff", color:"#00aaff", flexShrink:0, width:80 }}>
          <span>SEND</span>
        </button>
      </div>
    </div>
  );
}

// ─── Progress Bar ─────────────────────────────────────────────────────────────
function ProgressBar({ value, color = "#00ffcc", label, sublabel }) {
  return (
    <div style={{ marginBottom:16 }}>
      <div style={{ display:"flex", justifyContent:"space-between", marginBottom:6, fontSize:11 }}>
        <span style={{ color:"#3a6a58", letterSpacing:2 }}>{label}</span>
        <span style={{ color, fontWeight:700, textShadow:`0 0 6px ${color}` }}>{value}%</span>
      </div>
      <div style={{ height:6, background:"rgba(255,255,255,0.05)", borderRadius:0, overflow:"hidden", position:"relative" }}>
        <div className="bar-fill" style={{
          height:"100%", width:`${value}%`, background:color,
          boxShadow:`0 0 10px ${color}`,
          backgroundImage:`linear-gradient(90deg,${color}88,${color},${color}88)`,
          backgroundSize:"200% 100%", animation:"shimmer 2s infinite",
        }} />
      </div>
      {sublabel && <div style={{ fontSize:9, color:"#3a6a58", letterSpacing:1, marginTop:3 }}>{sublabel}</div>}
    </div>
  );
}

// ─── System Monitor ───────────────────────────────────────────────────────────
function SystemMonitor({ stats }) {
  return (
    <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
      {/* CPU */}
      <div className="glass glow-box-green corner-tl corner-br" style={{ position:"relative", padding:16 }}>
        <div className="orbitron" style={{ fontSize:9, letterSpacing:3, color:"#3a6a58", marginBottom:14 }}>CPU CORES</div>
        {stats.cpuCores.map((v, i) => (
          <div key={i} style={{ display:"flex", alignItems:"center", gap:8, marginBottom:6 }}>
            <span style={{ fontSize:9, color:"#3a6a58", width:40 }}>CORE {i}</span>
            <div style={{ flex:1, height:4, background:"rgba(0,255,204,0.08)" }}>
              <div className="bar-fill" style={{ height:"100%", width:`${v}%`, background:"#00ffcc", boxShadow:"0 0 6px #00ffcc" }} />
            </div>
            <span style={{ fontSize:9, color:"#00ffcc", width:28, textAlign:"right" }}>{v}%</span>
          </div>
        ))}
      </div>

      {/* RAM */}
      <div className="glass glow-box-blue corner-tl corner-br" style={{ position:"relative", padding:16 }}>
        <div className="orbitron" style={{ fontSize:9, letterSpacing:3, color:"#3a6a58", marginBottom:14 }}>MEMORY</div>
        <ProgressBar value={stats.ram} color="#00aaff" label="RAM USAGE" sublabel={`${(stats.ram * 0.128).toFixed(1)} GB / 12.8 GB`} />
        <ProgressBar value={stats.swap} color="#aa00ff" label="SWAP" sublabel={`${(stats.swap * 0.032).toFixed(1)} GB / 3.2 GB`} />
        <ProgressBar value={stats.disk} color="#00ff88" label="DISK I/O" sublabel="NVMe SSD — 3,400 MB/s" />
      </div>

      {/* Network */}
      <div className="glass glow-box-purple corner-tl corner-br" style={{ position:"relative", padding:16 }}>
        <div className="orbitron" style={{ fontSize:9, letterSpacing:3, color:"#3a6a58", marginBottom:14 }}>NETWORK</div>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8 }}>
          {[
            { label:"UPLOAD", value:`${stats.netUp} MB/s`, color:"#aa00ff" },
            { label:"DOWNLOAD", value:`${stats.netDown} MB/s`, color:"#00aaff" },
            { label:"LATENCY", value:`${stats.latency} ms`, color:"#00ffcc" },
            { label:"CLIENTS", value:stats.clients, color:"#00ff88" },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ background:"rgba(255,255,255,0.02)", border:"1px solid rgba(255,255,255,0.06)", padding:"10px 12px" }}>
              <div style={{ fontSize:8, letterSpacing:2, color:"#3a6a58", marginBottom:4 }}>{label}</div>
              <div style={{ fontSize:16, fontFamily:"Orbitron,monospace", color, textShadow:`0 0 8px ${color}`, fontWeight:700 }}>{value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Alerts */}
      <div className="glass glow-box-red corner-tl corner-br" style={{ position:"relative", padding:16 }}>
        <div className="orbitron" style={{ fontSize:9, letterSpacing:3, color:"#3a6a58", marginBottom:14 }}>THREAT MATRIX</div>
        {stats.threats.map((t, i) => (
          <div key={i} style={{ display:"flex", alignItems:"center", gap:8, marginBottom:8, padding:"6px 10px", background:"rgba(255,0,60,0.05)", border:"1px solid rgba(255,0,60,0.15)" }}>
            <div style={{ width:5, height:5, borderRadius:"50%", background: t.level === "HIGH" ? "#ff003c" : "#ffaa00",
              boxShadow:`0 0 6px ${t.level === "HIGH" ? "#ff003c" : "#ffaa00"}` }} className="pulse" />
            <div style={{ flex:1 }}>
              <div style={{ fontSize:9, color: t.level === "HIGH" ? "#ff003c" : "#ffaa00", letterSpacing:1 }}>{t.level} — {t.type}</div>
              <div style={{ fontSize:9, color:"#3a6a58" }}>{t.src}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Settings Panel ───────────────────────────────────────────────────────────
function SettingsPanel({ wsUrl, setWsUrl, onReconnect }) {
  const [saved, setSaved] = useState(false);
  const save = () => { sfx.send(); setSaved(true); setTimeout(() => setSaved(false), 2000); onReconnect(); };
  return (
    <div className="glass corner-tl corner-br" style={{ position:"relative", padding:24, maxWidth:600 }}>
      <div className="orbitron glow-green" style={{ fontSize:13, letterSpacing:4, marginBottom:24 }}>SYSTEM CONFIGURATION</div>

      <div style={{ marginBottom:20 }}>
        <div style={{ fontSize:10, letterSpacing:2, color:"#3a6a58", marginBottom:8 }}>WEBSOCKET ENDPOINT</div>
        <input className="neo-input" value={wsUrl} onChange={e => setWsUrl(e.target.value)} />
      </div>

      {[
        { label:"AI MODEL", value:"NEO-CORTEX-v7 (Quantum)" },
        { label:"ENCRYPTION", value:"AES-4096 + Quantum Key" },
        { label:"LOG RETENTION", value:"50 entries (rolling)" },
        { label:"THEME", value:"CYBERPUNK DARK" },
        { label:"AUDIO", value:"ENABLED" },
      ].map(({ label, value }) => (
        <div key={label} style={{ display:"flex", justifyContent:"space-between", padding:"10px 0", borderBottom:"1px solid rgba(0,255,204,0.08)", fontSize:12 }}>
          <span style={{ color:"#3a6a58", letterSpacing:1 }}>{label}</span>
          <span style={{ color:"#00ffcc" }}>{value}</span>
        </div>
      ))}

      <div style={{ marginTop:20, display:"flex", gap:10 }}>
        <button className="neo-btn" onClick={save}><span>{saved ? "SAVED ✓" : "SAVE CONFIG"}</span></button>
        <button className="neo-btn" onClick={onReconnect} style={{ borderColor:"#00aaff", color:"#00aaff" }}><span>RECONNECT WS</span></button>
      </div>
    </div>
  );
}

// ─── Stats Cards (Dashboard) ──────────────────────────────────────────────────
function StatCard({ label, value, sub, color, icon }) {
  return (
    <div className="glass corner-tl corner-br" style={{
      position:"relative", padding:20,
      boxShadow:`0 0 20px ${color}22, inset 0 0 20px ${color}08`,
      borderColor:`${color}44`,
    }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start" }}>
        <div>
          <div style={{ fontSize:9, letterSpacing:3, color:"#3a6a58", marginBottom:8 }}>{label}</div>
          <div style={{ fontFamily:"Orbitron,monospace", fontSize:28, fontWeight:900, color, textShadow:`0 0 12px ${color}` }}>{value}</div>
          {sub && <div style={{ fontSize:10, color:"#3a6a58", marginTop:4 }}>{sub}</div>}
        </div>
        <div style={{ fontSize:28, opacity:0.4 }}>{icon}</div>
      </div>
    </div>
  );
}

// ─── Dashboard View ───────────────────────────────────────────────────────────
function Dashboard({ logs, stats, sendWS, messages, setMessages }) {
  return (
    <div style={{ display:"grid", gridTemplateRows:"auto 1fr", gap:12, height:"100%" }}>
      {/* Stat cards */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:12 }}>
        <StatCard label="ACTIVE CLIENTS" value={stats.clients}   sub="Connected nodes"       color="#00ffcc" icon="◈" />
        <StatCard label="CPU LOAD"        value={`${stats.cpu}%`} sub="8-core quantum proc"   color="#00aaff" icon="⬡" />
        <StatCard label="MEMORY"          value={`${stats.ram}%`} sub={`${(stats.ram*0.128).toFixed(1)}GB used`} color="#aa00ff" icon="▣" />
        <StatCard label="THREATS"         value={stats.threats.length} sub="Active alerts"    color="#ff003c" icon="⚠" />
      </div>
      {/* Log + Chat */}
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12, overflow:"hidden" }}>
        <LogPanel logs={logs} />
        <ChatPanel sendWS={sendWS} messages={messages} setMessages={setMessages} />
      </div>
    </div>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────
export default function App() {
  const [messages, setMessages] = useState([
  { id: 0, isAI: true, text: "NEO AI SYSTEM v3.0 initialized..." }
]);
  const [activeTab, setActiveTab] = useState("dashboard");
  const [wsUrl, setWsUrl] = useState("ws://127.0.0.1:8000/ws");
  const [wsStatus, setWsStatus] = useState("DISCONNECTED");
  const [logs, setLogs] = useState([]);
  const [notifs, setNotifs] = useState([]);
  const [stats, setStats] = useState({
    cpu: 42, ram: 67, swap: 28, disk: 55, netUp: 12.4, netDown: 34.1,
    latency: 8, clients: 7,
    cpuCores: [45, 72, 31, 88, 56, 23, 67, 41],
    threats: [
      { level:"HIGH", type:"SQL INJECTION", src:"194.67.x.x" },
      { level:"MED",  type:"PORT SCAN",     src:"10.0.0.x" },
    ],
  });

const useFPS = () => {
  const [fps, setFps] = useState(0);
  const frame = useRef(0);
  const last = useRef(performance.now());

  useEffect(() => {
    let raf;

    const loop = (now) => {
      frame.current++;

      if (now - last.current >= 1000) {
        setFps(frame.current);
        frame.current = 0;
        last.current = now;
      }

      raf = requestAnimationFrame(loop);
    };

    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, []);

  return fps;
};

  const wsRef = useRef(null);
  const notifIdRef = useRef(0);

  // Push a log entry
  const pushLog = useCallback((msg, type = "INFO") => {
    setLogs(l => [...l.slice(-49), { id: Date.now() + Math.random(), msg, type, time: timestamp() }]);
  }, []);

  // Push notification
  const pushNotif = useCallback((msg, type = "INFO", color = "#00ffcc") => {
    const id = ++notifIdRef.current;
    setNotifs(n => [...n, { id, msg, type, color, time: timestamp() }]);
    sfx.notify();
    setTimeout(() => setNotifs(n => n.filter(x => x.id !== id)), 5000);
  }, []);

  const dismissNotif = (id) => setNotifs(n => n.filter(x => x.id !== id));

  // WebSocket
  const connectWS = useCallback(() => {
  if (wsRef.current) return;

  setWsStatus("CONNECTING");
  pushLog("Initiating WebSocket connection...", "SYS");

  try {
    const ws = new WebSocket("ws://127.0.0.1:8000/ws");

    wsRef.current = ws;

    ws.onopen = () => {
      setWsStatus("CONNECTED");
      pushLog("WebSocket connected", "SUCCESS");
      pushNotif("Connected", "WS", "#00ffcc");
    };

    ws.onmessage = (e) => {
  const msg = e.data;

  // logs me show hoga
  pushLog(msg, "AI");

  // 🔥 UI chat me show hoga
  setMessages(prev => [
    ...prev,
    { sender: "neo", text: msg }
  ]);
};

ws.onerror = (err) => {
  console.log("WS ERROR:", err);
};

    ws.onclose = () => {
      setWsStatus("DISCONNECTED");
      wsRef.current = null;
      setTimeout(() => connectWS(), 2000);
    };

  } catch (err) {
    console.log("WS FAILED:", err);
  }
}, []);

  const sendWS = (msg) => {
    pushLog(`TX → ${msg}`, "DATA");
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(msg);
    } else {
      pushLog("WebSocket not connected. Message queued locally.", "WARN");
    }
  };

  // Boot sequence
  useEffect(() => {
    const msgs = [
      ["NEO AI SYSTEM v3.0 — BOOTSTRAP SEQUENCE INITIATED", "SYS"],
      ["Loading quantum kernel modules…", "INFO"],
      ["Neural network cores: 32/32 ONLINE", "SUCCESS"],
      ["Cryptographic subsystem initialized — AES-4096", "SUCCESS"],
      ["Threat detection engine: ACTIVE", "INFO"],
      ["Memory management unit calibrated", "INFO"],
      ["All systems nominal. Ready.", "SUCCESS"],
    ];
    msgs.forEach(([m, t], i) => setTimeout(() => pushLog(m, t), i * 400));
    setTimeout(() => connectWS(), msgs.length * 400 + 500);
    return () => wsRef.current?.close();
  }, []);

  // Simulate live stats
  useEffect(() => {
    const iv = setInterval(() => {
      setStats(s => ({
        ...s,
        cpu: Math.max(5, Math.min(99, s.cpu + randBetween(-8, 8))),
        ram: Math.max(30, Math.min(95, s.ram + randBetween(-3, 3))),
        swap: Math.max(5, Math.min(80, s.swap + randBetween(-2, 2))),
        disk: Math.max(10, Math.min(90, s.disk + randBetween(-5, 5))),
        netUp: Math.max(0.1, (s.netUp + randBetween(-30, 30) / 10)).toFixed(1) * 1,
        netDown: Math.max(0.1, (s.netDown + randBetween(-50, 50) / 10)).toFixed(1) * 1,
        latency: Math.max(1, s.latency + randBetween(-2, 2)),
        clients: Math.max(1, s.clients + (Math.random() > 0.8 ? randBetween(-1, 1) : 0)),
        cpuCores: s.cpuCores.map(v => Math.max(2, Math.min(99, v + randBetween(-12, 12)))),
      }));
      if (Math.random() > 0.7) pushLog(
        [
          `Heartbeat packet received from node ${randBetween(1,32)}.`,
          `Cache flush: ${randBetween(100,999)} MB reclaimed.`,
          `Auth token rotated. New TTL: 180s.`,
          `Packet inspection: ${randBetween(1000,9999)} frames/sec.`,
          `Quantum key exchange with peer ${randBetween(10,99)}.`,
          `Log checkpoint written to persistent storage.`,
        ][randBetween(0, 5)],
        ["INFO","DATA","SYS","SUCCESS"][randBetween(0,3)]
      );
    }, 1500);
    return () => clearInterval(iv);
  }, [pushLog]);

  const TABS = {
  dashboard: (
    <Dashboard 
      logs={logs} 
      stats={stats} 
      sendWS={sendWS} 
      messages={messages} 
      setMessages={setMessages} 
    />
  ),

  logs: (
    <div style={{ height: "100%" }}>
      <LogPanel logs={logs} />
    </div>
  ),

  chat: (
    <div style={{ height: "100%" }}>
      <ChatPanel sendWS={sendWS} />
    </div>
  ),

  monitor: (
    <div style={{ overflowY: "auto", height: "100%" }}>
      <SystemMonitor stats={stats} />
    </div>
  ),

  settings: (
    <SettingsPanel 
      wsUrl={wsUrl} 
      setWsUrl={setWsUrl} 
      onReconnect={connectWS} 
    />
  ),
};

  return (
    <>
      <style>{GLOBAL_CSS}</style>
      <div className="scanlines" style={{ position:"fixed", inset:0, zIndex:9999, pointerEvents:"none" }} />
      <MatrixRain />
      <div className="hex-bg" />

      <NotificationCenter notifs={notifs} dismiss={dismissNotif} />
      <Header wsStatus={wsStatus} sysOnline={true} />
      <Sidebar active={activeTab} setActive={setActiveTab} />

      <main style={{
        position:"fixed", top:56, left:180, right:0, bottom:0,
        padding:12, overflow:"hidden", zIndex:10,
      }}>
        {TABS[activeTab]}
      </main>
    </>
  );


const [uptime, setUptime] = useState(0);

useEffect(() => {
  const iv = setInterval(() => setUptime(u => u + 1), 1000);
  return () => clearInterval(iv);
}, []);

const parseCommand = (cmd) => {
  if (cmd === "clear") {
    setLogs([]);
    return "Logs cleared.";
  }
  if (cmd === "status") {
    return "All systems operational.";
  }
  return null;
};
const local = parseCommand(txt);
if (local) {
  setMessages(m => [...m, {
    id: Date.now(),
    isAI: true,
    text: local,
    time: timestamp()
  }]);
  return;
}

const [theme, setTheme] = useState("dark");

const fpsColor = fps > 50 ? "#00ffcc" : fps > 30 ? "#ffaa00" : "#ff003c";
 
<div style={{ fontSize:9, color:"#3a6a58" }}>
  FPS: <span style={{ color:"#00ffcc" }}>{fps}</span>
</div>
}