import React, { useEffect, useMemo, useState, useRef } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { createRoot } from "react-dom/client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { motion, AnimatePresence } from "framer-motion";
import { 
  AlertCircle, Bot, Check, Clock, Copy, Download, Eye, EyeOff, File, FileText, 
  Focus, LogOut, Menu, Moon, Pin, Plus, RefreshCw, Search, Send, Sun, 
  ThumbsDown, ThumbsUp, Trash2, Upload, X, Shield, Users, CreditCard, 
  Compass, Sparkles, ChevronRight, HelpCircle, FileDown, Folder, Database,
  Settings, User, Lock, Mail, Paperclip, SlidersHorizontal, ChevronDown
} from "lucide-react";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" ? "http://127.0.0.1:8000" : window.location.origin);
const API = `${API_BASE.replace(/\/$/, "")}/api`;
const isDev = import.meta.env.DEV;

function logApi(method, path, status, detail = "") {
  if (isDev) console.info("[ONGC API]", { baseUrl: API_BASE, method, path, status, detail });
}

async function readApiError(res) {
  const data = await res.json().catch(() => ({}));
  if (res.status === 409) return "An account with this email already exists.";
  if (res.status === 422) return "Please check the entered details.";
  if (res.status === 401) return "Invalid email or password.";
  if (res.status === 403) return "You do not have permission to perform this action.";
  if (res.status >= 500) return "An internal server error occurred.";
  return data.detail || "Unable to continue.";
}

function storedTokens() {
  try {
    return JSON.parse(sessionStorage.getItem("tokens") || "null");
  } catch {
    sessionStorage.removeItem("tokens");
    return null;
  }
}

// Crisp official red block ONGC logo with circle well symbol and Sanskrit details
function ongcLogo(sizeClass = "h-11 w-11") {
  return (
    <img src="/ongc_logo.png" className={`${sizeClass} object-contain shrink-0 rounded-lg`} alt="ONGC Logo" style={{ filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.1))' }} />
  );
}

function formatBytes(bytes) {
  if (!bytes) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function formatDate(isoString) {
  if (!isoString) return "";
  try {
    const s = String(isoString);
    const d = new Date(s.endsWith("Z") || s.includes("+") || s.includes("-", 10) ? s : s + "Z");
    return d.toLocaleDateString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

function formatTime(isoString) {
  if (!isoString) return "";
  try {
    const s = String(isoString);
    const d = new Date(s.endsWith("Z") || s.includes("+") || s.includes("-", 10) ? s : s + "Z");
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

function ProtectedRoute({ children, tokens, authChecked }) {
  const location = useLocation();

  if (!authChecked) {
    return (
      <main className="grid min-h-screen place-items-center bg-[#0b0f19] text-slate-300">
        <div className="rounded-2xl border border-slate-800 bg-[#0f172a] px-6 py-5 text-sm font-semibold shadow-md animate-pulse">
          Checking secure session...
        </div>
      </main>
    );
  }

  if (!tokens) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}

function PublicRoute({ children, tokens, authChecked }) {
  if (!authChecked) {
    return (
      <main className="grid min-h-screen place-items-center bg-[#0b0f19] text-slate-300">
        <div className="rounded-2xl border border-slate-800 bg-[#0f172a] px-6 py-5 text-sm font-semibold shadow-md animate-pulse">
          Checking secure session...
        </div>
      </main>
    );
  }

  if (tokens) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

function App() {
  const [auth, setAuth] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [dark, setDark] = useState(() => {
    return localStorage.getItem("theme") !== "light";
  });

  useEffect(() => {
    if (dark) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);

  useEffect(() => {
    async function verifySession() {
      const saved = storedTokens();
      if (!saved?.access_token) {
        sessionStorage.removeItem("tokens");
        setAuth(null);
        setAuthChecked(true);
        return;
      }
      try {
        const res = await fetch(`${API}/auth/me`, {
          headers: { Authorization: `Bearer ${saved.access_token}` }
        });
        if (!res.ok) {
          sessionStorage.removeItem("tokens");
          sessionStorage.removeItem("active_session_id");
          setAuth(null);
        } else {
          setAuth({ tokens: saved, user: await res.json() });
        }
      } catch {
        sessionStorage.removeItem("tokens");
        setAuth(null);
      } finally {
        setAuthChecked(true);
      }
    }
    verifySession();
  }, []);

  const handleLogout = () => {
    const token = auth?.tokens?.access_token;
    if (token) fetch(`${API}/auth/logout`, { method: "POST", headers: { Authorization: `Bearer ${token}` } }).catch(() => {});
    sessionStorage.removeItem("tokens");
    sessionStorage.removeItem("active_session_id");
    if (auth?.user?.id) sessionStorage.removeItem(`active_session_id_${auth.user.id}`);
    localStorage.removeItem("tokens");
    localStorage.removeItem("active_session_id");
    localStorage.removeItem("focusDocumentId");
    setAuth(null);
  };

  const tokens = auth?.tokens || null;

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute tokens={tokens} authChecked={authChecked}>
              <Dashboard key={auth?.user?.id ?? "unauthenticated"} tokens={tokens} user={auth?.user} onLogout={handleLogout} dark={dark} setDark={setDark} />
            </ProtectedRoute>
          }
        />
        <Route path="/chat" element={<Navigate to="/dashboard" replace />} />
        <Route path="/history" element={<Navigate to="/dashboard" replace />} />
        <Route path="/settings" element={<Navigate to="/dashboard" replace />} />
        <Route path="/uploads" element={<Navigate to="/dashboard" replace />} />
        <Route path="/analytics" element={<Navigate to="/dashboard" replace />} />

        <Route
          path="/login"
          element={
            <PublicRoute tokens={tokens} authChecked={authChecked}>
              <Login onLogin={setAuth} dark={dark} setDark={setDark} />
            </PublicRoute>
          }
        />

        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

function Login({ onLogin, dark, setDark }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [mode, setMode] = useState("login");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    const path = mode === "login" ? "/auth/login" : "/auth/register";
    const payload = mode === "login" ? { email, password } : { email, password, full_name: name || email.split("@")[0], role: "employee" };
    try {
      const res = await fetch(`${API}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      logApi("POST", path, res.status);
      if (!res.ok) {
        setError(await readApiError(res));
        return;
      }
      if (mode === "register") {
        setMode("login");
        setPassword("");
        setName("");
        setError("Account created. Please login with your new credentials.");
        return;
      }
      const data = await res.json();
      const me = await fetch(`${API}/auth/me`, { headers: { Authorization: `Bearer ${data.access_token}` } });
      logApi("GET", "/auth/me", me.status);
      if (!me.ok) throw new Error("Authentication validation failed");
      
      sessionStorage.setItem("tokens", JSON.stringify(data));
      onLogin({ tokens: data, user: await me.json() });
    } catch {
      setError("Unable to connect to the server. Please verify that the backend is running.");
    } finally {
      setLoading(false);
    }
  }

  // Staggered transitions
  const leftContainerVariants = {
    hidden: { opacity: 0, x: -30 },
    visible: { opacity: 1, x: 0, transition: { duration: 0.6, ease: "easeOut", staggerChildren: 0.12 } }
  };

  const rightContainerVariants = {
    hidden: { opacity: 0, scale: 0.98 },
    visible: { opacity: 1, scale: 1, transition: { duration: 0.5, ease: "easeOut", staggerChildren: 0.1 } }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 15 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" } }
  };

  return (
    <main className="min-h-screen bg-[#070b13] text-slate-100 transition-colors duration-300 relative flex items-center justify-center p-4 select-none">
      
      {/* Dark mode toggle — top right corner of login page */}
      <button
        onClick={() => setDark(!dark)}
        className="absolute top-4 right-4 z-50 flex h-9 w-9 items-center justify-center rounded-xl border border-slate-700/60 bg-slate-900/80 text-slate-300 hover:text-white hover:border-slate-500 transition-all duration-200 backdrop-blur-sm"
        title={dark ? "Switch to light theme" : "Switch to dark theme"}
      >
        {dark ? <Sun size={15} /> : <Moon size={15} />}
      </button>

      {/* Container — split card structure */}
      <div className="w-full max-w-5xl rounded-3xl overflow-hidden border border-slate-800 bg-[#0c1221]/90 shadow-2xl grid grid-cols-1 lg:grid-cols-[1.12fr_0.88fr] min-h-[600px] relative">
        
        {/* Left Panel: Hero side */}
        <motion.section 
          variants={leftContainerVariants}
          initial="hidden"
          animate="visible"
          className="relative flex flex-col justify-between bg-gradient-to-br from-[#0a1835] via-[#050e23] to-[#040817] p-8 lg:p-12 overflow-hidden border-r border-slate-800/60"
        >
          {/* Glow backgrounds */}
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_30%,#0057a8,transparent)] opacity-20 pointer-events-none" />
          <div className="absolute inset-0 bg-grid-white/[0.02] pointer-events-none" />

          {/* Logo & Header — z-10 to stay above background image */}
          <div className="space-y-4 relative z-10">
            <motion.div variants={itemVariants} className="flex justify-start">
              {ongcLogo("w-20 h-20 object-contain shrink-0")}
            </motion.div>
            <motion.div variants={itemVariants} className="space-y-1">
              <h1 className="text-3xl font-black tracking-tight leading-tight text-white">ONGC IntelliAssist</h1>
              <p className="text-xs font-bold uppercase tracking-widest text-blue-400">Enterprise AI Knowledge Assistant</p>
            </motion.div>
          </div>

          {/* Tagline & Description — z-10 to stay above rig image */}
          <motion.div variants={itemVariants} className="my-auto py-10 relative z-10 max-w-md space-y-4">
            <h3 className="text-lg font-bold text-blue-100">Intelligent search. Trusted answers.</h3>
            <p className="text-sm text-slate-300 leading-relaxed">
              Access ONGC's corporate knowledge, policies, SOPs, and technical documents with the power of AI.
            </p>
            <div className="flex flex-wrap gap-2 mt-4">
              {["HSE Policies", "HR Leave", "Procurement", "Drilling SOPs", "Live Web Search"].map((tag) => (
                <span key={tag} className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-blue-900/40 border border-blue-700/40 text-blue-300">{tag}</span>
              ))}
            </div>
          </motion.div>

          {/* Rig image — z-0, behind text */}
          <img 
            src="/rig_sunset.png" 
            alt="Offshore Rig illustration"
            className="absolute bottom-0 left-0 w-full h-[40%] object-cover object-center opacity-50 mix-blend-lighten pointer-events-none z-0" 
          />
        </motion.section>

        {/* Right Panel: Form */}
        <section className="flex items-center justify-center p-8 lg:p-12 bg-[#0c1221]/50 backdrop-blur-md">
          <motion.div 
            variants={rightContainerVariants}
            initial="hidden"
            animate="visible"
            className="w-full max-w-md space-y-6"
          >
            <motion.div variants={itemVariants}>
              <h2 className="text-2xl font-bold tracking-tight text-white">
                {mode === "login" ? "Welcome Back!" : "Create Account"}
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                {mode === "login" ? "Sign in to continue to ONGC IntelliAssist" : "Sign up to join ONGC IntelliAssist"}
              </p>
            </motion.div>

            <motion.form variants={itemVariants} onSubmit={submit} className="space-y-4">
              {mode === "register" && (
                <motion.div variants={itemVariants} className="relative">
                  <span className="absolute left-3.5 top-[22px] -translate-y-1/2 text-slate-400 z-10">
                    <User size={16} />
                  </span>
                  <input 
                    className="field" 
                    placeholder="Full Name" 
                    value={name} 
                    onChange={(e) => setName(e.target.value)} 
                    required 
                  />
                </motion.div>
              )}

              <motion.div variants={itemVariants} className="relative">
                <span className="absolute left-3.5 top-[22px] -translate-y-1/2 text-slate-400 z-10">
                  <Mail size={16} />
                </span>
                <input 
                  className="field" 
                  type="email" 
                  required 
                  autoComplete="email" 
                  placeholder="Email Address" 
                  value={email} 
                  onChange={(e) => setEmail(e.target.value)} 
                />
              </motion.div>

              <motion.div variants={itemVariants} className="relative">
                <span className="absolute left-3.5 top-[22px] -translate-y-1/2 text-slate-400 z-10">
                  <Lock size={16} />
                </span>
                <input
                  className="field"
                  placeholder="Password"
                  type={showPassword ? "text" : "password"}
                  required
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <button
                  type="button"
                  className="absolute right-3.5 top-[22px] -translate-y-1/2 flex h-8 w-8 cursor-pointer items-center justify-center rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors z-10"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </motion.div>

              {error && (
                <motion.div 
                  initial={{ opacity: 0, scale: 0.98 }} 
                  animate={{ opacity: 1, scale: 1 }} 
                  className="rounded-xl bg-red-950/20 p-3.5 text-xs text-red-300 border border-red-900/40 flex items-start gap-2.5"
                >
                  <AlertCircle size={16} className="shrink-0 mt-0.5" />
                  <span>{error}</span>
                </motion.div>
              )}

              <motion.button 
                variants={itemVariants}
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
                disabled={loading} 
                className="w-full h-12 text-sm font-bold bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-500 hover:to-blue-600 active:scale-[0.99] text-white rounded-xl shadow-md shadow-blue-900/40 transition-all flex items-center justify-center gap-2"
              >
                <span>{mode === "login" ? "Sign In" : "Create Account"}</span>
                {loading && <RefreshCw className="animate-spin text-white" size={14} />}
              </motion.button>

              <motion.div variants={itemVariants} className="text-center mt-4">
                <button
                  type="button"
                  onClick={() => {
                    setMode(mode === "login" ? "register" : "login");
                    setError("");
                  }}
                  className="text-xs text-blue-400 hover:text-blue-300 font-semibold transition-colors"
                >
                  {mode === "login" ? "Don't have an account? Sign Up" : "Already have an account? Sign In"}
                </button>
              </motion.div>
            </motion.form>

            <motion.div variants={itemVariants} className="text-center pt-4">
              <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">
                Powered by RAG · Groq · Tavily · Ollama
              </span>
            </motion.div>
          </motion.div>
        </section>
      </div>
    </main>
  );
}

function groupSessions(sessions) {
  const groups = { today: [], yesterday: [], last7: [], older: [] };
  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterdayStart = new Date(todayStart);
  yesterdayStart.setDate(yesterdayStart.getDate() - 1);
  const last7Start = new Date(todayStart);
  last7Start.setDate(last7Start.getDate() - 7);

  sessions.forEach((s) => {
    const date = new Date(s.updated_at || s.created_at);
    if (date >= todayStart) {
      groups.today.push(s);
    } else if (date >= yesterdayStart) {
      groups.yesterday.push(s);
    } else if (date >= last7Start) {
      groups.last7.push(s);
    } else {
      groups.older.push(s);
    }
  });
  return groups;
}

function Dashboard({ tokens, user, onLogout, dark, setDark }) {
  const headers = useMemo(() => ({ Authorization: `Bearer ${tokens.access_token}` }), [tokens]);
  const [sessions, setSessions] = useState([]);
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(() => {
    const saved = sessionStorage.getItem(`active_session_id_${user.id}`);
    return saved ? parseInt(saved, 10) : null;
  });
  const [question, setQuestion] = useState("");
  const [docs, setDocs] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [query, setQuery] = useState("");
  const [docSearch, setDocSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState("Thinking...");
  const [uploading, setUploading] = useState(false);
  const [toasts, setToasts] = useState([]);
  const [focusDocumentId, setFocusDocumentId] = useState(null);
  const [activeLibraryTab, setActiveLibraryTab] = useState("uploads");
  
  // Sidebar state
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    const saved = localStorage.getItem("sidebar_open");
    return saved !== null ? saved === "true" : true;
  });
  
  // Library panel state matching image 2
  const [showLibrary, setShowLibrary] = useState(true);
  const [developerMode, setDeveloperMode] = useState(() => localStorage.getItem("developerMode") === "true");
  const [showScrollButton, setShowScrollButton] = useState(false);

  // Knowledge Base page state (admin only)
  const [page, setPage] = useState("chat");
  const [kbStats, setKbStats] = useState(null);
  const [kbDocs, setKbDocs] = useState([]);
  const [kbDocSearch, setKbDocSearch] = useState("");
  const [kbUploading, setKbUploading] = useState(false);
  const [kbMetaDoc, setKbMetaDoc] = useState(null);
  
  const chatContainerRef = useRef(null);
  const loadControllerRef = useRef(null);
  const streamControllerRef = useRef(null);
  const isNearBottomRef = useRef(true);
  const focusDoc = useMemo(() => {
    if (!focusDocumentId) return null;
    // Check user uploads first, then KB docs
    return docs.find((d) => d.id === focusDocumentId) || kbDocs.find((d) => d.id === focusDocumentId) || null;
  }, [docs, kbDocs, focusDocumentId]);

  const filteredDocs = useMemo(() => {
    return docs.filter((d) => d.filename.toLowerCase().includes(docSearch.toLowerCase()));
  }, [docs, docSearch]);

  const filteredKbDocs = useMemo(() => {
    const q = kbDocSearch.toLowerCase().trim();
    if (!q) return kbDocs;
    return kbDocs.filter((d) =>
      (d.filename || "").toLowerCase().includes(q) ||
      (d.summary || "").toLowerCase().includes(q)
    );
  }, [kbDocs, kbDocSearch]);

  function toggleSidebar(val) {
    setSidebarOpen(val);
    localStorage.setItem("sidebar_open", val ? "true" : "false");
  }

  function enterFocusMode(docId) {
    setFocusDocumentId(docId);
  }

  function exitFocusMode() {
    setFocusDocumentId(null);
  }

  function showToast(message, type = "success") {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3000);
  }

  useEffect(() => () => {
    loadControllerRef.current?.abort();
    streamControllerRef.current?.abort();
  }, []);

  useEffect(() => {
    localStorage.removeItem("focusDocumentId");
  }, []);

  useEffect(() => {
    localStorage.setItem("developerMode", developerMode ? "true" : "false");
  }, [developerMode]);

  useEffect(() => {
    function handleShortcut(event) {
      if (event.ctrlKey && event.altKey && event.key.toLowerCase() === "d") {
        event.preventDefault();
        setDeveloperMode((value) => !value);
        showToast("Developer mode toggled.");
      }
    }
    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, []);

  async function callApi(path, method = "GET", body = null, isMultipart = false, signal = undefined, retries = 2) {
    const opts = {
      method,
      headers: {
        Authorization: `Bearer ${tokens.access_token}`
      },
      signal
    };
    if (body) {
      if (isMultipart) {
        opts.body = body;
      } else {
        opts.headers["Content-Type"] = "application/json";
        opts.body = JSON.stringify(body);
      }
    }

    let lastError;
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const res = await fetch(`${API}${path}`, opts);
        logApi(method, path, res.status);
        if (res.status === 401) {
          onLogout();
          throw new Error("Unauthorized");
        }
        return res;
      } catch (err) {
        lastError = err;
        if (attempt < retries && err.name !== "AbortError" && !signal?.aborted) {
          await new Promise(resolve => setTimeout(resolve, 500 * (attempt + 1)));
        }
      }
    }
    throw lastError;
  }

  function analyticsPath(id = sessionId) {
    const params = new URLSearchParams();
    if (id) params.set("session_id", id);
    if (developerMode) params.set("include_routing", "true");
    const queryString = params.toString();
    return `/analytics${queryString ? `?${queryString}` : ""}`;
  }

  async function load() {
    const controller = new AbortController();
    loadControllerRef.current?.abort();
    loadControllerRef.current = controller;
    try {
      const promises = [
        callApi("/chat/sessions", "GET", null, false, controller.signal).then((r) => r.ok ? r.json() : []),
        callApi("/documents", "GET", null, false, controller.signal).then((r) => r.ok ? r.json() : []),
        callApi(analyticsPath(), "GET", null, false, controller.signal).then((r) => r.ok ? r.json() : null)
      ];
      // KB summaries are loaded for ALL users (needed for focus badge on KB docs)
      promises.push(
        callApi("/documents/kb/summaries", "GET", null, false, controller.signal).then((r) => r.ok ? r.json() : [])
      );
      if (user?.role === "admin") {
        promises.push(
          callApi("/documents/kb/stats", "GET", null, false, controller.signal).then((r) => r.ok ? r.json() : null)
        );
      }
      const results = await Promise.all(promises);
      const [s, d, a] = results;
      setSessions(Array.isArray(s) ? s : []);
      setDocs(Array.isArray(d) ? d : []);
      setAnalytics(a);
      // KB docs available for all users (for focus badge)
      setKbDocs(Array.isArray(results[3]) ? results[3] : []);
      if (user?.role === "admin") {
        setKbStats(results[4] || null);
      }
    } catch (e) {
      if (e.name !== "AbortError" && e.message !== "Unauthorized") {
        showToast("Error syncing data from server.", "error");
      }
    }
  }

  useEffect(() => {
    load();
  }, [sessionId, developerMode]);

  useEffect(() => {
    if (sessionId) {
      openSession(sessionId, false);
    }
  }, []);

  const scrollToBottom = (behavior = "smooth") => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior
      });
    }
  };

  const handleScroll = () => {
    const container = chatContainerRef.current;
    if (!container) return;
    const threshold = 150;
    const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < threshold;
    isNearBottomRef.current = isNearBottom;
    if (isNearBottom) setShowScrollButton(false);
  };

  useEffect(() => {
    if (messages.length === 0) return;
    const lastMessage = messages[messages.length - 1];
    if (lastMessage.role === "user") {
      scrollToBottom("smooth");
      isNearBottomRef.current = true;
      setShowScrollButton(false);
    } else {
      const container = chatContainerRef.current;
      if (container) {
        const threshold = 250;
        const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < threshold;
        if (isNearBottom) {
          scrollToBottom("smooth");
          isNearBottomRef.current = true;
          setShowScrollButton(false);
        } else if (lastMessage.role === "assistant") {
          // Show this only for a newly-arrived response below the viewport.
          setShowScrollButton(true);
        }
      }
    }
  }, [messages, loading]);

  async function openSession(id, refreshAnalytics = true) {
    // Abort existing streams to prevent data leaking
    streamControllerRef.current?.abort();
    setLoading(false);
    setLoadingStatus("Thinking...");

    setSessionId(id);
    sessionStorage.setItem(`active_session_id_${user.id}`, id);
    setFocusDocumentId(null);
    setShowScrollButton(false);
    isNearBottomRef.current = true;
    try {
      const data = await callApi(`/chat/sessions/${id}/messages`).then((r) => r.json());
      setMessages(Array.isArray(data) ? data : []);
      if (refreshAnalytics) {
        const a = await callApi(analyticsPath(id)).then((r) => r.ok ? r.json() : null);
        setAnalytics(a);
      }
      setTimeout(() => scrollToBottom("auto"), 50);
    } catch (e) {
      if (e.message !== "Unauthorized" && e.name !== "AbortError") {
        showToast("Failed to retrieve chat messages.", "error");
      }
    }
  }

  async function send(text = question) {
    if (!text.trim()) return;
    setLoading(true);
    setIsGenerating(true);
    setLoadingStatus("Thinking...");
    const localQuestion = text;

    // Abort previous stream on the same channel
    streamControllerRef.current?.abort();
    const controller = new AbortController();
    streamControllerRef.current = controller;
    
    const assistantTempId = `a-${Date.now()}`;
    let assistantStarted = false;
    setQuestion("");
    setMessages((old) => [...old, { role: "user", content: localQuestion, id: `u-${Date.now()}`, created_at: new Date().toISOString() }]);

    try {
      const res = await fetch(`${API}/chat/stream`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${tokens.access_token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ question: localQuestion, session_id: sessionId, mode: "auto", focus_document_id: focusDocumentId }),
        signal: controller.signal
      });
      logApi("POST", "/chat/stream", res.status);
      if (res.status === 401) {
        onLogout();
        return;
      }
      if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: "Request failed." }));
        setMessages((old) => [...old, {
          id: `e-${Date.now()}`,
          role: "assistant",
          content: `I could not answer this request: ${error.detail || "Please try again."}`,
          source: "System Error",
          domain: "Error",
          error: true,
          response_time_ms: 0,
          citations: [],
          created_at: new Date().toISOString()
        }]);
        setLoading(false);
        setIsGenerating(false);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.trim()) continue;
          const event = JSON.parse(line);

          if (event.event === "status") {
            setLoadingStatus(event.message || "Thinking...");
          }

          if (event.event === "error") {
            setLoading(false);
            setIsGenerating(false);
            const errorId = assistantStarted ? assistantTempId : `e-${Date.now()}`;
            setMessages((old) => {
              if (assistantStarted) {
                return old.map((m) => m.id === assistantTempId ? { ...m, error: true, content: event.message || "The assistant could not complete this response.", source: null, streaming: false } : m);
              }
              return [...old, {
                id: errorId,
                role: "assistant",
                error: true,
                content: event.message || "The assistant could not complete this response.",
                source: null,
                domain: "Error",
                response_time_ms: null,
                citations: [],
                created_at: new Date().toISOString()
              }];
            });
          }

          if (event.event === "meta") {
            setSessionId(event.session_id);
            sessionStorage.setItem(`active_session_id_${user.id}`, event.session_id);
          }

          if (event.event === "token") {
            if (!assistantStarted) {
              assistantStarted = true;
              // FIRST TOKEN ARRIVED — THIS IS THE MOMENT TO SHOW THE STOP BUTTON (ChatGPT-style)
              setIsGenerating(true);
              setLoading(false);
              setMessages((old) => [...old, {
                id: assistantTempId,
                role: "assistant",
                content: event.text || "",
                source: "Groq AI",
                domain: null,
                response_time_ms: null,
                citations: [],
                streaming: true,
                created_at: new Date().toISOString()
              }]);
            } else {
              setMessages((old) => old.map((m) => (
                m.id === assistantTempId ? { ...m, content: `${m.content}${event.text || ""}` } : m
              )));
            }
          }

          if (event.event === "done") {
            setSessionId(event.session_id);
            sessionStorage.setItem(`active_session_id_${user.id}`, event.session_id);
            setMessages((old) => old.map((m) => (
              m.id === assistantTempId
                ? {
                    ...m,
                    id: event.assistant_message_id || assistantTempId,
                    source: event.source,
                    domain: event.domain,
                    response_time_ms: event.response_time_ms,
                    citations: event.citations || [],
                    streaming: false
                  }
                : m
            )));
          }
        }
      }
    } catch (e) {
      if (e.name === "AbortError") {
        // User clicked Stop — finalize the streaming message cleanly (ChatGPT-style)
        setMessages((old) => old.map((m) =>
          m.id === assistantTempId && m.streaming
            ? { ...m, streaming: false, source: m.source || "Stopped", domain: m.domain || null }
            : m
        ));
      } else if (e.message !== "Unauthorized") {
        setMessages((old) => [...old, {
          id: `e-${Date.now()}`,
          role: "assistant",
          content: "Unable to connect to the server. Please verify that the backend is running.",
          source: null,
          domain: "Error",
          error: true,
          response_time_ms: 0,
          citations: [],
          created_at: new Date().toISOString()
        }]);
      }
    } finally {
      setLoading(false);
      setIsGenerating(false);
      setLoadingStatus("Thinking...");
      load();
    }
  }

  function startNewChat() {
    streamControllerRef.current?.abort();
    setLoading(false);
    setIsGenerating(false);
    setLoadingStatus("Thinking...");
    
    setSessionId(null);
    sessionStorage.removeItem(`active_session_id_${user.id}`);
    setFocusDocumentId(null);
    setShowScrollButton(false);
    isNearBottomRef.current = true;
    setMessages([]);
    setQuestion("");
  }

  async function deleteSession(id, event) {
    event.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this chat session?")) return;
    try {
      await callApi(`/chat/sessions/${id}`, "DELETE");
      showToast("Chat deleted successfully.");
      if (sessionId === id) startNewChat();
      load();
    } catch (e) {
      if (e.message !== "Unauthorized") {
        showToast("Error deleting chat session.", "error");
      }
    }
  }

  async function togglePin(id, event) {
    event.stopPropagation();
    try {
      await callApi(`/chat/sessions/${id}/pin`, "PATCH");
      showToast("Chat priority updated.");
      load();
    } catch (e) {
      if (e.message !== "Unauthorized") {
        showToast("Error toggling pin status.", "error");
      }
    }
  }

  async function renameSession(id, currentTitle) {
    const newTitle = window.prompt("Rename this chat session:", currentTitle);
    if (!newTitle || !newTitle.trim()) return;
    try {
      await callApi(`/chat/sessions/${id}?title=${encodeURIComponent(newTitle)}`, "PATCH");
      showToast("Chat renamed.");
      load();
    } catch (e) {
      if (e.message !== "Unauthorized") {
        showToast("Error renaming chat session.", "error");
      }
    }
  }

  async function deleteDoc(doc, event) {
    event.stopPropagation();
    if (!window.confirm(`Are you sure you want to delete "${doc.filename}"?\n\nThis will physically remove the file, delete its chunks, metadata, and refresh the search indices.`)) return;
    try {
      const res = await callApi(`/documents/${doc.id}`, "DELETE");
      if (res.ok) {
        showToast(`Document "${doc.filename}" removed.`);
        load();
      } else {
        showToast("Failed to delete document.", "error");
      }
    } catch (e) {
      if (e.message !== "Unauthorized") {
        showToast("Error deleting document.", "error");
      }
    }
  }

  async function toggleDoc(docId, event) {
    event.stopPropagation();
    try {
      await callApi(`/documents/${docId}/toggle`, "PATCH");
      showToast("Document toggled.");
      load();
    } catch (e) {
      if (e.message !== "Unauthorized") {
        showToast("Error toggling document.", "error");
      }
    }
  }

  async function upload(event) {
    const files = Array.from(event.target.files);
    if (!files.length) return;
    setUploading(true);
    showToast("Processing document. Extracting text & calculating embeddings...");
    // Optimistic update: show files in library immediately
    const tempDocs = files.map((f, i) => ({
      id: `temp-${Date.now()}-${i}`,
      filename: f.name,
      size_bytes: f.size,
      created_at: new Date().toISOString(),
      status: "indexing",
      enabled: true,
    }));
    setDocs((prev) => [...tempDocs, ...prev]);
    const form = new FormData();
    for (const file of files) form.append("files", file);
    try {
      const res = await callApi("/documents", "POST", form, true);
      if (res.ok) {
        showToast("Documents uploaded and indexed successfully!");
      } else {
        const err = await res.json().catch(() => ({}));
        showToast(err.detail || "Upload failed.", "error");
        // Remove optimistic items on failure
        setDocs((prev) => prev.filter((d) => !String(d.id).startsWith("temp-")));
      }
    } catch (e) {
      if (e.message !== "Unauthorized") {
        showToast("Network upload error.", "error");
        setDocs((prev) => prev.filter((d) => !String(d.id).startsWith("temp-")));
      }
    } finally {
      setUploading(false);
      event.target.value = "";
      load(); // Always refresh to get real server state
    }
  }

  async function reindexDoc(doc, event) {
    event.stopPropagation();
    showToast(`Re-indexing "${doc.filename}"...`);
    try {
      const res = await callApi(`/documents/${doc.id}/reindex`, "POST");
      if (res.ok) {
        showToast(`Document "${doc.filename}" re-indexed successfully.`);
        load();
      } else {
        showToast("Failed to re-index document.", "error");
      }
    } catch (e) {
      if (e.message !== "Unauthorized") {
        showToast("Error re-indexing document.", "error");
      }
    }
  }

  async function uploadKB(event) {
    const files = Array.from(event.target.files);
    if (!files.length) return;
    setKbUploading(true);
    showToast("Processing Knowledge Base reports. Extracting text & calculating embeddings...");
    const tempDocs = files.map((f, i) => ({
      id: `temp-${Date.now()}-${i}`,
      filename: f.name,
      size_bytes: f.size,
      created_at: new Date().toISOString(),
      status: "indexing",
      enabled: true,
      is_kb: true,
      total_chunks: 0,
      total_pages: 0,
      embedding_status: "Pending",
      indexed_status: "Not Indexed",
    }));
    setKbDocs((prev) => [...tempDocs, ...prev]);
    const form = new FormData();
    for (const file of files) form.append("files", file);
    try {
      const res = await callApi("/documents?is_kb=true", "POST", form, true);
      if (res.ok) {
        showToast("Knowledge Base reports uploaded and indexed successfully!");
      } else {
        const err = await res.json().catch(() => ({}));
        showToast(err.detail || "KB upload failed.", "error");
        setKbDocs((prev) => prev.filter((d) => !String(d.id).startsWith("temp-")));
      }
    } catch (e) {
      if (e.message !== "Unauthorized") {
        showToast("Network upload error.", "error");
        setKbDocs((prev) => prev.filter((d) => !String(d.id).startsWith("temp-")));
      }
    } finally {
      setKbUploading(false);
      event.target.value = "";
      load();
    }
  }

  async function deleteKbDoc(doc, event) {
    if (event) event.stopPropagation();
    if (!window.confirm(`Are you sure you want to delete "${doc.filename}" from the Permanent Knowledge Base?\n\nThis will remove the report, its chunks, embeddings, and refresh the search indices.`)) return;
    try {
      const res = await callApi(`/documents/${doc.id}`, "DELETE");
      if (res.ok) {
        showToast(`Knowledge Base report "${doc.filename}" removed.`);
        load();
      } else {
        showToast("Failed to delete KB report.", "error");
      }
    } catch (e) {
      if (e.message !== "Unauthorized") {
        showToast("Error deleting KB report.", "error");
      }
    }
  }

  async function reindexKbDoc(doc, event) {
    if (event) event.stopPropagation();
    showToast(`Re-indexing KB report "${doc.filename}"...`);
    try {
      const res = await callApi(`/documents/${doc.id}/reindex`, "POST");
      if (res.ok) {
        showToast(`KB report "${doc.filename}" re-indexed successfully.`);
        load();
      } else {
        showToast("Failed to re-index KB report.", "error");
      }
    } catch (e) {
      if (e.message !== "Unauthorized") {
        showToast("Error re-indexing KB report.", "error");
      }
    }
  }

  async function viewKbMetadata(doc, event) {
    if (event) event.stopPropagation();
    try {
      const res = await callApi(`/documents/${doc.id}/metadata`, "GET");
      if (res.ok) {
        const meta = await res.json();
        setKbMetaDoc(meta);
      } else {
        showToast("Failed to retrieve metadata.", "error");
      }
    } catch (e) {
      if (e.message !== "Unauthorized") {
        showToast("Error loading metadata.", "error");
      }
    }
  }

  function exportChat() {
    if (messages.length === 0) {
      showToast("No messages to export.", "error");
      return;
    }
    const text = messages.map((m) => `${m.role.toUpperCase()} [${formatTime(m.created_at)}]: ${m.content}`).join("\n\n");
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ongc-intelliassist-chat-${sessionId || "new"}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    showToast("Conversation exported.");
  }

  async function regenerate() {
    const userMsgs = messages.filter((m) => m.role === "user");
    if (userMsgs.length === 0) return;
    const lastQuestion = userMsgs[userMsgs.length - 1].content;
    send(lastQuestion);
  }

  const filteredSessions = useMemo(() => {
    const items = sessions.filter((s) => s.title.toLowerCase().includes(query.toLowerCase()));
    return items.sort((a, b) => {
      if (a.pinned && !b.pinned) return -1;
      if (!a.pinned && b.pinned) return 1;
      return new Date(b.updated_at) - new Date(a.updated_at);
    });
  }, [sessions, query]);

  // Sidebar content (Image 2 style)
  const renderSidebarContent = () => (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 p-4 shrink-0">
        <div className="flex items-center gap-3">
          {ongcLogo("h-10 w-10")}
          <div className="min-w-0 flex-1">
            <h1 className="font-bold text-sm tracking-tight text-slate-950 dark:text-white leading-tight">ONGC IntelliAssist</h1>
            <p className="text-[10px] text-slate-400 dark:text-slate-400 font-semibold uppercase tracking-wider">Enterprise Assistant</p>
          </div>
        </div>
      </div>
      
      <div className="p-4 flex flex-col gap-3 shrink-0 border-b border-slate-100 dark:border-slate-850">
        {/* Blue "+ New Chat" matching image 2 layout */}
        <button className={`primary w-full h-11 text-[15px] font-bold shadow-md ${page === "chat" ? "shadow-ongc-blue/15" : "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700"}`} onClick={() => { setPage("chat"); startNewChat(); }} title="Start a fresh chat">
          <Plus size={16} />New Chat
        </button>

        {/* Admin-only Knowledge Base — immediately below New Chat per spec */}
        {user?.role === "admin" && (
          <button
            className={`w-full h-11 text-[15px] font-bold rounded-xl flex items-center justify-center gap-2 transition-all duration-200 border shadow-sm ${
              page === "kb"
                ? "bg-gradient-to-r from-emerald-600 to-teal-700 text-white border-transparent shadow-emerald-900/20"
                : "bg-white dark:bg-slate-800/50 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-emerald-500/50 hover:text-emerald-700 dark:hover:text-emerald-400"
            }`}
            onClick={() => setPage("kb")}
            title="Manage Permanent Knowledge Base (Admin Only)"
          >
            <Database size={16} />📚 Knowledge Base
          </button>
        )}
        
        {/* Search Input and Filter */}
        <div className="flex items-center gap-2">
          <div className="flex-1 flex items-center gap-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950 px-3 transition focus-within:border-ongc-blue dark:focus-within:border-blue-500">
            <Search className="text-slate-400 shrink-0" size={15} />
            <input className="h-10 w-full bg-transparent text-xs outline-none text-slate-800 dark:text-slate-100" placeholder="Search chats..." value={query} onChange={(e) => setQuery(e.target.value)} />
          </div>
          <button className="icon-btn h-10 w-10 shrink-0 border-slate-200/80" title="Filter options">
            <SlidersHorizontal size={14} />
          </button>
        </div>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto px-3.5 py-4 custom-scrollbar space-y-4">
        {filteredSessions.length === 0 ? (
          <p className="text-center text-xs text-slate-400 mt-6 font-medium">No active chats found</p>
        ) : (
          (() => {
            const groups = groupSessions(filteredSessions);
            const renderSection = (title, items) => {
              if (items.length === 0) return null;
              return (
                <div key={title} className="space-y-1">
                  <h3 className="px-2 pb-1 text-[9.5px] font-bold tracking-widest uppercase text-slate-400 dark:text-slate-500">{title}</h3>
                  <AnimatePresence>
                    {items.map((s) => (
                      <motion.div 
                        layout
                        key={s.id} 
                        className={`group flex items-center gap-1 rounded-xl p-2.5 transition-all duration-200 ${sessionId === s.id ? "bg-blue-50/60 text-ongc-blue dark:bg-blue-950/20 dark:text-blue-300 font-semibold" : "hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300"}`}
                      >
                        <div className="min-w-0 flex-1">
                          <button onClick={() => { openSession(s.id); if(window.innerWidth < 768) toggleSidebar(false); }} className="w-full truncate text-left text-xs" title={s.title}>
                            {s.title}
                          </button>
                          <div className="text-[9px] text-slate-400 dark:text-slate-500 font-semibold mt-0.5">
                            {formatTime(s.updated_at || s.created_at)}
                          </div>
                        </div>
                        <div className="flex opacity-0 group-hover:opacity-100 transition-opacity">
                          <button className={`mini-icon h-7 w-7 ${s.pinned ? "text-amber-500 opacity-100" : ""}`} onClick={(e) => togglePin(s.id, e)} title={s.pinned ? "Unpin chat" : "Pin chat"}>
                            <Pin size={12} className={s.pinned ? "fill-amber-500" : ""} />
                          </button>
                          <button className="mini-icon h-7 w-7" onClick={() => renameSession(s.id, s.title)} title="Rename chat">
                            <FileText size={12} />
                          </button>
                          <button className="mini-icon h-7 w-7 hover:text-red-500" onClick={(e) => deleteSession(s.id, e)} title="Delete chat">
                            <Trash2 size={12} />
                          </button>
                        </div>
                        {s.pinned && <Pin size={11} className="text-amber-500 fill-amber-500 ml-1 group-hover:hidden" />}
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>
              );
            };

            return [
              renderSection("Today", groups.today),
              renderSection("Yesterday", groups.yesterday),
              renderSection("Last 7 Days", groups.last7),
              renderSection("Older", groups.older)
            ];
          })()
        )}
      </div>

      {/* User profile section matching image 2 at sidebar footer */}
      <div className="border-t border-slate-200 dark:border-slate-800 p-4 shrink-0 flex items-center justify-between gap-3 bg-slate-50/50 dark:bg-slate-900/40">
        <div className="flex items-center gap-3 min-w-0">
          <div className="h-10 w-10 rounded-full bg-ongc-blue text-white flex items-center justify-center font-bold text-sm shrink-0 shadow-sm">
            {user?.full_name?.charAt(0).toUpperCase() || user?.email?.charAt(0).toUpperCase() || "U"}
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-xs font-bold text-slate-800 dark:text-white truncate">{user?.full_name || "Employee"}</div>
            <div className="text-[10px] text-slate-400 dark:text-slate-500 truncate mt-0.5">{user?.email}</div>
          </div>
        </div>
        <ChevronDown size={15} className="text-slate-400 dark:text-slate-500 cursor-pointer hover:text-slate-700 dark:hover:text-slate-300" />
      </div>
    </div>
  );

  return (
    <main className="flex h-screen w-screen bg-slate-50 text-slate-950 dark:bg-[#070b13] dark:text-slate-100 transition-colors duration-300 relative overflow-hidden">
      {/* Toast HUD */}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((t) => (
          <div key={t.id} className={`toast-animate flex items-center gap-2 rounded-xl px-4.5 py-3 text-sm font-semibold shadow-lg text-white ${t.type === "error" ? "bg-red-600" : "bg-gradient-to-r from-ongc-blue to-ongc-deep"}`}>
            <AlertCircle size={16} />
            {t.message}
          </div>
        ))}
      </div>

      {/* Mobile Drawer Overlay */}
      <div className="md:hidden">
        <AnimatePresence>
          {sidebarOpen && (
            <>
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.4 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-40 bg-black backdrop-blur-sm" 
                onClick={() => toggleSidebar(false)} 
              />
              <motion.aside
                initial={{ x: "-100%" }}
                animate={{ x: 0 }}
                exit={{ x: "-100%" }}
                transition={{ duration: 0.3, ease: "easeOut" }}
                className="fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 h-full overflow-hidden"
              >
                {renderSidebarContent()}
              </motion.aside>
            </>
          )}
        </AnimatePresence>
      </div>

      {/* Desktop Sidebar (Slides) */}
      <motion.aside 
        animate={{ width: sidebarOpen ? 320 : 0 }}
        transition={{ duration: 0.3, ease: "easeInOut" }}
        className="hidden md:flex flex-col border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 h-full shrink-0 overflow-hidden"
        style={{ borderRightWidth: sidebarOpen ? 1 : 0 }}
      >
        <div className="w-[320px] h-full flex flex-col overflow-hidden">
          {renderSidebarContent()}
        </div>
      </motion.aside>

      {/* Main chat layout */}
      <section className="flex min-w-0 flex-1 flex-col h-full overflow-hidden transition-colors duration-300">
        
        {/* Top Header layout exactly matching image 2 */}
        <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-6 dark:border-slate-800 dark:bg-slate-900 transition-colors duration-300 shrink-0">
          <div className="flex items-center gap-3">
            <button 
              className="icon-btn h-10 w-10 shrink-0" 
              onClick={() => toggleSidebar(!sidebarOpen)} 
              title={sidebarOpen ? "Close sidebar" : "Open sidebar"}
            >
              <Menu size={16} />
            </button>
            {ongcLogo("h-9 w-9")}
            <div>
              <h2 className="font-bold text-sm text-slate-950 dark:text-white leading-tight">ONGC IntelliAssist</h2>
              <p className="text-[10px] text-slate-400 dark:text-slate-400 font-semibold tracking-wide">Your AI Assistant for ONGC Knowledge</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button className="icon-btn h-10 w-10" onClick={() => setDark(!dark)} title={dark ? "Switch to light theme" : "Switch to dark theme"}>
              {dark ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            {/* Show/Hide Library Sidebar Toggle Button */}
            <button 
              className="px-3.5 py-2 text-xs font-bold rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition shadow-sm"
              onClick={() => setShowLibrary(!showLibrary)}
            >
              {showLibrary ? "Hide Library" : "Show Library"}
            </button>
            <button className="icon-btn h-10 w-10 hover:bg-red-50 dark:hover:bg-red-955/20 hover:text-red-650" onClick={onLogout} title="Logout">
              <LogOut size={16} />
            </button>
          </div>
        </header>

        {/* Dashboard grid layout */}
        {page === "chat" ? (
        <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[1fr_auto] overflow-hidden">
          <div className="flex min-w-0 flex-col h-full overflow-hidden relative bg-slate-50/50 dark:bg-[#0c1221]/40">
            
            {/* Scrollable chat body */}
            <div 
              ref={chatContainerRef}
              onScroll={handleScroll}
              className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6 custom-scrollbar"
            >
              {messages.length === 0 ? (
                (docs.length === 0 && user?.role !== "admin") ? (
                  <div className="flex flex-col items-center justify-center h-full space-y-6">
                    <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-slate-100 dark:bg-slate-800 text-slate-400">
                      <Folder size={40} />
                    </div>
                    <div className="text-center space-y-2">
                      <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-200">No documents uploaded.</h2>
                      <p className="text-slate-500 dark:text-slate-400 max-w-md mx-auto">
                        Please upload one or more PDF documents to ask questions about them, or ask about ONGC policies, manuals, and corporate information directly.
                      </p>
                    </div>
                    <label className={`cursor-pointer inline-flex items-center gap-2 rounded-xl bg-ongc-blue hover:bg-blue-600 text-white px-6 py-3 font-bold shadow-md transition-all ${uploading ? "opacity-50 pointer-events-none" : ""}`}>
                      <Upload size={18} />
                      {uploading ? "Uploading..." : "Upload Documents"}
                      <input type="file" multiple accept=".pdf,.docx,.txt" className="hidden" onChange={upload} disabled={uploading} />
                    </label>
                  </div>
                ) : (
                  <Welcome analytics={analytics} onAsk={send} />
                )
              ) : (
                <div className="space-y-6">
                  <AnimatePresence initial={false}>
                    {messages.map((m) => (
                      <Message 
                        key={m.id} 
                        message={m} 
                        callApi={callApi}
                        onRegenerate={regenerate} 
                        isLast={messages[messages.length - 1].id === m.id} 
                        showToast={showToast} 
                        showTechnical={developerMode || user?.role === "admin"}
                      />
                    ))}
                  </AnimatePresence>
                </div>
              )}
              {loading && <ResponseLoader status={loadingStatus} />}
            </div>

            {/* Smart Scroll: floating button */}
            {showScrollButton && (
              <button
                onClick={() => {
                  scrollToBottom("smooth");
                  setShowScrollButton(false);
                }}
                className="absolute bottom-28 left-1/2 -translate-x-1/2 z-30 flex items-center gap-1.5 rounded-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 px-4 py-2 text-xs font-bold shadow-md text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 hover:scale-105 active:scale-[0.98] transition-all duration-200"
              >
                <Clock size={12} /> Jump to latest
              </button>
            )}

            {/* Composer area */}
            <div className="border-t border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 transition-colors duration-300 shrink-0">
              <div className="max-w-4xl mx-auto space-y-2.5">
                {focusDoc && (
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-ongc-blue/10 dark:bg-blue-900/30 border border-ongc-blue/30 dark:border-blue-700 px-3 py-1 text-xs font-bold text-ongc-blue dark:text-blue-300">
                      <Focus size={11} />
                      Focused: {focusDoc.filename}
                    </span>
                    <button
                      className="inline-flex items-center gap-1 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 px-2.5 py-1 text-xs font-semibold text-slate-500 dark:text-slate-400 hover:text-red-500 hover:border-red-200 dark:hover:border-red-800 transition-all duration-150"
                      onClick={exitFocusMode}
                      title="Exit Focus Mode"
                    >
                      <X size={11} /> Exit Focus
                    </button>
                  </div>
                )}
                
                {/* Input composer — ChatGPT-style with paperclip */}
                <div className="relative flex items-center rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950 focus-within:ring-2 focus-within:ring-ongc-blue/15 focus-within:border-ongc-blue dark:focus-within:border-blue-500 transition-all duration-300 shadow-inner px-4 py-2">
                  {/* Paperclip upload icon */}
                  <label
                    htmlFor="composer-file-upload"
                    className="cursor-pointer text-slate-400 hover:text-ongc-blue dark:hover:text-blue-400 mr-3 transition-colors duration-200"
                    title="Attach document"
                  >
                    <Paperclip size={16} />
                    <input
                      id="composer-file-upload"
                      type="file"
                      multiple
                      accept=".pdf,.docx,.txt"
                      className="hidden"
                      onChange={upload}
                      disabled={uploading}
                    />
                  </label>
                  <textarea
                    className="w-full resize-none bg-transparent py-2 text-[15px] text-slate-800 dark:text-slate-100 outline-none placeholder-slate-400 min-h-[38px] max-h-40 custom-scrollbar font-medium"
                    placeholder={focusDoc ? `Ask anything about ${focusDoc.filename}...` : "Ask about ONGC policies, HSE manuals, drilling SOPs, or current affairs..."}
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
                    rows={1}
                  />
                  
                  {/* Send / Stop Button — ChatGPT-style semantics:
                      - Show Stop button ONLY while the assistant is ACTIVELY streaming tokens (isGenerating=true).
                      - Before the first token arrives (HTTP loading) OR after generation is done: Show Send button.
                  */}
                  {isGenerating ? (
                    <button 
                      onClick={() => { streamControllerRef.current?.abort(); setIsGenerating(false); setLoading(false); }}
                      className="inline-flex h-9 shrink-0 items-center justify-center gap-1.5 rounded-xl bg-red-600 px-3 text-xs font-bold text-white shadow-sm hover:bg-red-500 hover:scale-[1.03] active:scale-[0.97] transition-all duration-200 ml-2"
                      title="Stop"
                    >
                      <X size={14} /> Stop
                    </button>
                  ) : (
                    <button 
                      onClick={() => send()} 
                      disabled={!question.trim() || loading}
                      className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-gradient-to-r from-ongc-blue to-ongc-deep text-white shadow-sm hover:scale-[1.03] active:scale-[0.97] transition-all duration-200 disabled:opacity-40 disabled:scale-100 ml-2"
                      title="Send message"
                    >
                      <Send size={14} />
                    </button>
                  )}
                </div>
                {/* Disclaimer */}
                <div className="text-center text-[10.5px] text-slate-400 font-semibold tracking-wide">
                  ONGC IntelliAssist can make mistakes. Please verify important information.
                </div>
              </div>
            </div>
          </div>

          {/* Right Sidebar - Library Sidebar (Analytics removed for regular users) */}
          <AnimatePresence>
            {showLibrary && (
              <motion.aside 
                initial={{ width: 0, opacity: 0 }}
                animate={{ width: 360, opacity: 1 }}
                exit={{ width: 0, opacity: 0 }}
                transition={{ duration: 0.3 }}
                className="flex flex-col h-full border-l border-slate-200 bg-slate-50/50 p-6 dark:border-slate-800 dark:bg-slate-900/60 overflow-hidden shrink-0"
              >
                {/* Analytics — 4 metrics only, always visible */}
                <h3 className="mb-3 font-bold text-xs tracking-wider uppercase text-slate-400 dark:text-slate-500 shrink-0">Insights</h3>
                <div className="grid grid-cols-2 gap-2.5 mb-5 shrink-0">
                  <Metric label="Documents" value={analytics?.uploaded_documents ?? docs.length} />
                  <Metric label="Avg Latency" value={`${analytics?.average_response_time_ms ? (analytics.average_response_time_ms / 1000).toFixed(1) : 0}s`} />
                  <Metric label="Total Chats" value={analytics?.total_chats ?? 0} />
                  <Metric label="Questions Asked" value={analytics?.questions_asked ?? 0} />
                </div>
                {/* Admin extras */}
                {user?.role === "admin" && (
                  <div className="mb-5 shrink-0">
                    <Metric label="Total Users" value={analytics?.total_users ?? 0} />
                  </div>
                )}

                {/* === UPLOADS LIST === */}
                <div className="flex items-center justify-between mb-4 shrink-0">
                  <h3 className="font-bold text-xs tracking-wider uppercase text-slate-400 dark:text-slate-500">Uploaded Documents</h3>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-bold">{filteredDocs.length} files</span>
                </div>

                <div className="flex items-center gap-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 px-3 py-1 shrink-0 mb-4 focus-within:border-ongc-blue">
                  <Search className="text-slate-400 shrink-0" size={14} />
                  <input 
                    type="text" 
                    placeholder="Search uploads..." 
                    value={docSearch} 
                    onChange={(e) => setDocSearch(e.target.value)} 
                    className="w-full bg-transparent border-none outline-none py-1.5 text-xs text-slate-800 dark:text-slate-100" 
                  />
                </div>

                <div className="flex-1 overflow-y-auto space-y-3 pr-1 custom-scrollbar">
                  {filteredDocs.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-10 text-center text-slate-400 space-y-2">
                      <Folder size={24} className="text-slate-300 dark:text-slate-700" />
                      <p className="text-xs italic">No uploaded documents yet.</p>
                      <p className="text-[10px] text-slate-400">Upload using the paperclip icon in chat</p>
                    </div>
                  ) : (
                    <AnimatePresence>
                      {filteredDocs.map((doc) => {
                        const isFocused = focusDocumentId === doc.id;
                        const ext = doc.filename.split('.').pop().toLowerCase();
                        let fileIcon = <FileText size={18} className="text-slate-400 shrink-0 mt-0.5" />;
                        if (ext === "pdf") fileIcon = <FileText size={18} className="text-red-500 dark:text-red-400 shrink-0 mt-0.5" />;
                        else if (ext === "docx") fileIcon = <FileText size={18} className="text-blue-500 dark:text-blue-400 shrink-0 mt-0.5" />;
                        else if (ext === "txt") fileIcon = <FileText size={18} className="text-green-500 dark:text-green-400 shrink-0 mt-0.5" />;

                        return (
                          <motion.div 
                            layout
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            key={doc.id} 
                            className={`group relative flex flex-col gap-2 rounded-2xl border bg-white p-3.5 dark:bg-slate-900 shadow-sm transition-all duration-300 hover:border-ongc-blue/40 ${isFocused ? "border-ongc-blue dark:border-blue-500 ring-2 ring-ongc-blue/10 dark:ring-blue-500/10" : "border-slate-200 dark:border-slate-800"}`}
                          >
                            <div className="flex items-start gap-2.5">
                              {fileIcon}
                              <div className="min-w-0 flex-1">
                                <div className="text-xs font-bold text-slate-800 dark:text-slate-100 break-words leading-snug" title={doc.filename}>{doc.filename}</div>
                                <div className="flex flex-wrap gap-x-2 text-[10px] text-slate-400 font-semibold mt-1">
                                  <span>{formatBytes(doc.size_bytes)}</span>
                                  <span>•</span>
                                  <span>{formatDate(doc.created_at)}</span>
                                </div>
                              </div>
                              <button className="text-slate-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity shrink-0 p-1" onClick={(e) => deleteDoc(doc, e)} title="Delete document">
                                <Trash2 size={13} />
                              </button>
                            </div>
                            <div className="flex items-center gap-1.5 border-t border-slate-100 dark:border-slate-800 pt-2 justify-between">
                              <div className="flex items-center gap-1.5">
                                <span className="text-[8px] uppercase tracking-wider font-black text-slate-400">STATUS</span>
                                <span className="inline-flex items-center rounded-full bg-green-50 dark:bg-green-950/20 px-2.5 py-0.5 text-[9px] font-bold text-green-700 dark:text-green-400 border border-green-200 dark:border-green-900">
                                  {doc.status || "Indexed"}
                                </span>
                              </div>
                              <div className="flex items-center gap-2">
                                <button
                                  onClick={(e) => reindexDoc(doc, e)}
                                  className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[9px] font-bold border bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-700 hover:border-ongc-blue/50 hover:text-ongc-blue transition-all duration-200"
                                  title="Re-index document"
                                >
                                  <RefreshCw size={8} /> Re-index
                                </button>
                                <button
                                  onClick={() => isFocused ? exitFocusMode() : enterFocusMode(doc.id)}
                                  className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[9px] font-bold border transition-all duration-200 ${
                                    isFocused
                                      ? "bg-ongc-blue text-white border-ongc-blue"
                                      : "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-700 hover:border-ongc-blue/50 hover:text-ongc-blue"
                                  }`}
                                  title={isFocused ? "Exit Focus Mode" : "Focus on this document"}
                                >
                                  <Focus size={8} />
                                  {isFocused ? "Focused" : "Focus"}
                                </button>
                              </div>
                            </div>
                          </motion.div>
                        );
                      })}
                    </AnimatePresence>
                  )}
                </div>
              </motion.aside>
            )}
          </AnimatePresence>
        </div>
        ) : page === "kb" ? (
          <KnowledgeBasePage
            kbStats={kbStats}
            kbDocs={filteredKbDocs}
            kbDocSearch={kbDocSearch}
            setKbDocSearch={setKbDocSearch}
            kbUploading={kbUploading}
            uploadKB={uploadKB}
            deleteKbDoc={deleteKbDoc}
            reindexKbDoc={reindexKbDoc}
            viewKbMetadata={viewKbMetadata}
            focusDocumentId={focusDocumentId}
            enterFocusMode={enterFocusMode}
            exitFocusMode={exitFocusMode}
          />
        ) : null}

        {/* KB Metadata modal */}
        <AnimatePresence>
          {kbMetaDoc && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
              onClick={() => setKbMetaDoc(null)}
            >
              <motion.div
                initial={{ opacity: 0, y: 20, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 20 }}
                onClick={(e) => e.stopPropagation()}
                className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 shadow-2xl overflow-hidden"
              >
                <div className="flex items-center justify-between p-5 border-b border-slate-200 dark:border-slate-800">
                  <h3 className="font-bold text-slate-900 dark:text-white">Document Metadata</h3>
                  <button onClick={() => setKbMetaDoc(null)} className="mini-icon h-8 w-8 hover:bg-slate-100 dark:hover:bg-slate-800">
                    <X size={15} />
                  </button>
                </div>
                <div className="p-5 space-y-2.5 max-h-[60vh] overflow-y-auto custom-scrollbar">
                  {[
                    ["Filename", kbMetaDoc.filename],
                    ["Content Hash", kbMetaDoc.content_hash?.slice?.(0, 16) + "…"],
                    ["Content Type", kbMetaDoc.content_type],
                    ["Size", formatBytes(kbMetaDoc.size_bytes)],
                    ["Status", kbMetaDoc.status],
                    ["Enabled", kbMetaDoc.enabled ? "Yes" : "No"],
                    ["Knowledge Base", kbMetaDoc.is_kb ? "Permanent KB" : "User Upload"],
                    ["Total Pages", kbMetaDoc.total_pages],
                    ["Total Chunks", kbMetaDoc.total_chunks],
                    ["Document Type", kbMetaDoc.document_type],
                    ["Source", kbMetaDoc.source],
                    ["Uploaded At", formatDate(kbMetaDoc.created_at)],
                    ["Uploaded By ID", kbMetaDoc.uploaded_by_id ?? "admin"],
                  ].map(([label, value]) => (
                    <div key={label} className="flex gap-3 items-start text-xs border-b border-slate-100 dark:border-slate-800 pb-2 last:border-0">
                      <span className="w-32 shrink-0 text-[10px] uppercase tracking-widest text-slate-400 font-bold pt-0.5">{label}</span>
                      <span className="flex-1 font-semibold text-slate-700 dark:text-slate-200 break-all">{value ?? "—"}</span>
                    </div>
                  ))}
                  {kbMetaDoc.summary && (
                    <div className="pt-3">
                      <div className="text-[10px] uppercase tracking-widest text-slate-400 font-bold mb-2">AI Summary</div>
                      <p className="text-xs text-slate-600 dark:text-slate-300 font-medium leading-relaxed bg-slate-50 dark:bg-slate-800/50 p-3 rounded-xl border border-slate-100 dark:border-slate-800">{kbMetaDoc.summary}</p>
                    </div>
                  )}
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </section>
    </main>
  );
}

function KnowledgeBasePage({
  kbStats,
  kbDocs,
  kbDocSearch,
  setKbDocSearch,
  kbUploading,
  uploadKB,
  deleteKbDoc,
  reindexKbDoc,
  viewKbMetadata,
  focusDocumentId,
  enterFocusMode,
  exitFocusMode,
}) {
  const statsCards = [
    { label: "Total Reports", value: kbStats?.total_reports ?? 0, suffix: kbStats?.enabled_reports ? `(${kbStats.enabled_reports} active)` : "", icon: <FileText size={18} />, color: "from-blue-500 to-blue-700" },
    { label: "Total Chunks", value: kbStats?.total_chunks ?? 0, icon: <Sparkles size={18} />, color: "from-indigo-500 to-purple-700" },
    { label: "Total Embeddings", value: kbStats?.total_embeddings ?? 0, suffix: kbStats?.embedding_dimension ? ` · ${kbStats.embedding_dimension}d` : "", icon: <Database size={18} />, color: "from-fuchsia-500 to-pink-700" },
    { label: "Vector DB Status", value: kbStats?.vector_db_status ?? "Unknown", icon: <Shield size={18} />, color: (kbStats?.vector_db_status === "Healthy") ? "from-emerald-500 to-teal-700" : "from-amber-500 to-orange-700", badge: true },
    { label: "Last Indexed", value: kbStats?.last_indexed_time ? formatDate(kbStats.last_indexed_time) : "Never", icon: <Clock size={18} />, color: "from-slate-500 to-slate-700" },
    { label: "Storage Usage", value: formatBytes(kbStats?.storage_usage_bytes ?? 0), suffix: (kbStats?.files_storage_bytes ? ` · Docs ${formatBytes(kbStats.files_storage_bytes)}` : "") + (kbStats?.vectors_storage_bytes ? ` · Vecs ${formatBytes(kbStats.vectors_storage_bytes)}` : ""), icon: <Folder size={18} />, color: "from-orange-500 to-red-700" },
  ];

  return (
    <div className="flex min-w-0 flex-1 flex-col h-full overflow-hidden bg-slate-50 dark:bg-[#0c1221]/40">
      <div className="flex-1 overflow-y-auto p-5 md:p-8 space-y-7 custom-scrollbar">
        {/* Page title + actions */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-tr from-emerald-600 to-teal-700 text-white shadow-lg shadow-emerald-900/20">
                <Database size={24} />
              </div>
              <div>
                <h2 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white leading-tight">Permanent Knowledge Base</h2>
                <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold">Admin-managed ONGC corporate documents — always available to all users.</p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2.5">
            <div className="flex items-center gap-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-3.5 py-2.5 focus-within:ring-2 focus-within:ring-emerald-500/15 focus-within:border-emerald-600 dark:focus-within:border-emerald-500 transition-all">
              <Search className="text-slate-400 shrink-0" size={15} />
              <input
                type="text"
                placeholder="Search reports..."
                value={kbDocSearch}
                onChange={(e) => setKbDocSearch(e.target.value)}
                className="w-60 bg-transparent border-none outline-none text-xs text-slate-800 dark:text-slate-100 font-semibold"
              />
            </div>
            <label className={`cursor-pointer inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-700 hover:from-emerald-500 hover:to-teal-600 text-white px-5 py-2.5 text-xs font-bold shadow-md shadow-emerald-900/20 transition-all ${kbUploading ? "opacity-50 pointer-events-none" : ""}`}>
              <Upload size={15} />
              {kbUploading ? "Indexing..." : "Upload Report"}
              <input type="file" multiple accept=".pdf,.docx,.txt" className="hidden" onChange={uploadKB} disabled={kbUploading} />
            </label>
          </div>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
          {statsCards.map((s, idx) => (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.04 }}
              key={s.label}
              className="rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 shadow-sm overflow-hidden"
            >
              <div className={`h-1 w-full bg-gradient-to-r ${s.color}`} />
              <div className="p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <div className={`flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr ${s.color} text-white shadow-sm`}>
                    {s.icon}
                  </div>
                  {s.badge && (
                    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[9px] font-black border ${
                      (s.value === "Healthy" || s.value === "Indexed")
                        ? "bg-emerald-50 dark:bg-emerald-950/20 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-900"
                        : "bg-amber-50 dark:bg-amber-950/20 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-900"
                    }`}>
                      {s.value}
                    </span>
                  )}
                </div>
                <div>
                  <div className="text-[9px] font-black uppercase tracking-widest text-slate-400 dark:text-slate-500">{s.label}</div>
                  {!s.badge && (
                    <div className="mt-0.5 text-lg font-black text-slate-800 dark:text-white leading-tight">
                      {typeof s.value === "number" ? s.value.toLocaleString() : s.value}
                      {s.suffix && <span className="ml-1 text-[10px] font-bold text-slate-400 dark:text-slate-500 normal-case">{s.suffix}</span>}
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Reports */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-[11px] tracking-widest uppercase text-slate-400 dark:text-slate-500 flex items-center gap-2 pl-1">
              <FileDown size={12} /> Uploaded Reports <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400">{kbDocs.length}</span>
            </h3>
          </div>

          {kbDocs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-24 text-center space-y-5 rounded-2xl border-2 border-dashed border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-900/30">
              <div className="flex h-24 w-24 items-center justify-center rounded-3xl bg-slate-100 dark:bg-slate-800 text-slate-400">
                <Folder size={48} />
              </div>
              <div className="space-y-2 max-w-md">
                <h3 className="text-xl font-black text-slate-800 dark:text-slate-200">No Knowledge Base reports yet.</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 font-semibold leading-relaxed">
                  Upload Annual Reports, HR Manuals, Finance Reports, HSE Manuals, Circulars, Policies, Technical Documents, Tender Documents, and Sustainability Reports to populate the permanent index.
                </p>
              </div>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {kbDocs.map((doc, idx) => {
                const ext = (doc.filename || "").split(".").pop().toLowerCase();
                let fileIcon = <FileText size={20} className="text-slate-400 shrink-0 mt-0.5" />;
                if (ext === "pdf") fileIcon = <FileText size={20} className="text-red-500 dark:text-red-400 shrink-0 mt-0.5" />;
                else if (ext === "docx") fileIcon = <FileText size={20} className="text-blue-500 dark:text-blue-400 shrink-0 mt-0.5" />;
                else if (ext === "txt") fileIcon = <FileText size={20} className="text-green-500 dark:text-green-400 shrink-0 mt-0.5" />;

                const embedOk = doc.embedding_status === "Completed" || doc.status === "indexed";
                const indexOk = doc.indexed_status === "Indexed" || doc.status === "indexed";

                return (
                  <motion.div
                    layout
                    initial={{ opacity: 0, y: 14 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: Math.min(idx * 0.025, 0.4) }}
                    key={doc.id}
                    className="group rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 shadow-sm hover:shadow-md hover:border-emerald-500/30 dark:hover:border-emerald-500/30 transition-all duration-200 overflow-hidden"
                  >
                    <div className="h-1.5 w-full bg-gradient-to-r from-emerald-500 via-teal-500 to-emerald-600 opacity-90" />
                    <div className="p-5 space-y-4">
                      {/* Header row */}
                      <div className="flex items-start gap-3">
                        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-700">
                          {fileIcon}
                        </div>
                        <div className="min-w-0 flex-1 space-y-1">
                          <div className="text-sm font-black text-slate-800 dark:text-white break-words leading-snug" title={doc.filename}>{doc.filename}</div>
                          <div className="flex flex-wrap gap-x-2 text-[10.5px] text-slate-400 dark:text-slate-500 font-bold">
                            <span>Uploaded {formatDate(doc.created_at)}</span>
                            <span>·</span>
                            <span>{formatBytes(doc.size_bytes)}</span>
                          </div>
                        </div>
                      </div>

                      {/* Stats grid 2x2 */}
                      <div className="grid grid-cols-4 gap-2">
                        <div className="rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700/80 p-2 text-center">
                          <div className="text-[8.5px] font-black uppercase tracking-widest text-slate-400 dark:text-slate-500">Pages</div>
                          <div className="text-sm font-black text-slate-800 dark:text-white leading-tight mt-0.5">{doc.total_pages ?? 0}</div>
                        </div>
                        <div className="rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700/80 p-2 text-center">
                          <div className="text-[8.5px] font-black uppercase tracking-widest text-slate-400 dark:text-slate-500">Chunks</div>
                          <div className="text-sm font-black text-slate-800 dark:text-white leading-tight mt-0.5">{doc.total_chunks ?? 0}</div>
                        </div>
                        <div className="rounded-xl border p-2 text-center" style={{ borderColor: embedOk ? "rgb(16 185 129 / 0.25)" : "rgb(245 158 11 / 0.25)", backgroundColor: embedOk ? "rgb(16 185 129 / 0.06)" : "rgb(245 158 11 / 0.06)" }}>
                          <div className="text-[8.5px] font-black uppercase tracking-widest" style={{ color: embedOk ? "rgb(16 185 129)" : "rgb(245 158 11)" }}>Embedding</div>
                          <div className={`text-[10px] font-black leading-tight mt-0.5 ${embedOk ? "text-emerald-700 dark:text-emerald-400" : "text-amber-700 dark:text-amber-400"}`}>{doc.embedding_status || "Pending"}</div>
                        </div>
                        <div className="rounded-xl border p-2 text-center" style={{ borderColor: indexOk ? "rgb(16 185 129 / 0.25)" : "rgb(245 158 11 / 0.25)", backgroundColor: indexOk ? "rgb(16 185 129 / 0.06)" : "rgb(245 158 11 / 0.06)" }}>
                          <div className="text-[8.5px] font-black uppercase tracking-widest" style={{ color: indexOk ? "rgb(16 185 129)" : "rgb(245 158 11)" }}>Indexed</div>
                          <div className={`text-[10px] font-black leading-tight mt-0.5 ${indexOk ? "text-emerald-700 dark:text-emerald-400" : "text-amber-700 dark:text-amber-400"}`}>{doc.indexed_status || "Not"}</div>
                        </div>
                      </div>

                      {/* Summary preview if present */}
                      {doc.summary && (
                        <p className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-3 leading-relaxed font-medium bg-slate-50 dark:bg-slate-800/40 p-3 rounded-xl border border-slate-100 dark:border-slate-800">
                          {doc.summary}
                        </p>
                      )}

                      {/* Action buttons */}
                      <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
                        <button
                          onClick={(e) => viewKbMetadata(doc, e)}
                          className="inline-flex items-center gap-1 rounded-xl px-3 py-1.5 text-[10.5px] font-bold border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:border-blue-500/40 hover:text-blue-700 dark:hover:text-blue-400 transition-all duration-200"
                          title="View document metadata"
                        >
                          <Eye size={11} /> View Metadata
                        </button>
                        <button
                          onClick={(e) => reindexKbDoc(doc, e)}
                          className="inline-flex items-center gap-1 rounded-xl px-3 py-1.5 text-[10.5px] font-bold border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:border-amber-500/40 hover:text-amber-700 dark:hover:text-amber-400 transition-all duration-200"
                          title="Re-build embeddings for this report only"
                        >
                          <RefreshCw size={11} /> Re-index
                        </button>
                        <button
                          onClick={() => focusDocumentId === doc.id ? exitFocusMode() : enterFocusMode(doc.id)}
                          className={`inline-flex items-center gap-1 rounded-xl px-3 py-1.5 text-[10.5px] font-bold border transition-all duration-200 ${
                            focusDocumentId === doc.id
                              ? "bg-ongc-blue text-white border-ongc-blue"
                              : "border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:border-ongc-blue/50 hover:text-ongc-blue"
                          }`}
                          title={focusDocumentId === doc.id ? "Exit Focus Mode" : "Focus on this document — all queries will search only this report"}
                        >
                          <Focus size={11} />
                          {focusDocumentId === doc.id ? "Focused" : "Focus"}
                        </button>
                        <div className="flex-1" />
                        <button
                          onClick={(e) => deleteKbDoc(doc, e)}
                          className="inline-flex items-center gap-1 rounded-xl px-3 py-1.5 text-[10.5px] font-bold border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-500 hover:border-red-500/40 hover:text-red-600 dark:hover:text-red-400 transition-all duration-200"
                          title="Delete report from Permanent Knowledge Base"
                        >
                          <Trash2 size={11} /> Delete
                        </button>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Welcome({ analytics, onAsk }) {
  const prompts = [
    { icon: <Compass className="text-ongc-blue dark:text-blue-400 shrink-0" size={18} />, text: "Explain ONGC exploration workflow" },
    { icon: <Shield className="text-ongc-blue dark:text-blue-400 shrink-0" size={18} />, text: "What are the PPE requirements?" },
    { icon: <FileText className="text-ongc-blue dark:text-blue-400 shrink-0" size={18} />, text: "Summarize my uploaded document" },
    { icon: <Users className="text-ongc-blue dark:text-blue-400 shrink-0" size={18} />, text: "Explain ONGC HR leave policy" },
    { icon: <CreditCard className="text-ongc-blue dark:text-blue-400 shrink-0" size={18} />, text: "Explain procurement process" },
    { icon: <Settings className="text-ongc-blue dark:text-blue-400 shrink-0" size={18} />, text: "What is reservoir engineering?" }
  ];

  const domains = [
    { name: "HR Policies", icon: <Users size={16} />, desc: "Leave policy, benefits, and employee regulations." },
    { name: "Safety & HSE", icon: <Shield size={16} />, desc: "PPE safety standards, PTW rules, and hazards." },
    { name: "Finance Accounts", icon: <CreditCard size={16} />, desc: "Expense protocols, travel claims, and tenders." },
    { name: "Engineering & SOPs", icon: <Settings size={16} />, desc: "Exploration logs, reservoirs, and pipeline SOPs." }
  ];

  return (
    <div className="mx-auto max-w-3xl py-8 md:py-14 space-y-8 text-slate-800 dark:text-slate-200">
      <div className="text-center space-y-4">
        <motion.div 
          animate={{ scale: [1, 1.04, 1] }} 
          transition={{ repeat: Infinity, duration: 4, ease: "easeInOut" }}
          className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-tr from-ongc-blue to-ongc-deep text-white shadow-lg shadow-ongc-blue/15"
        >
          <Bot size={34} />
        </motion.div>
        <div className="space-y-1">
          <h2 className="text-3xl font-black tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-slate-900 via-slate-800 to-slate-700 dark:from-white dark:via-slate-200 dark:to-slate-400 leading-tight">
            Welcome to ONGC IntelliAssist
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 max-w-lg mx-auto leading-relaxed font-semibold">
            Enterprise AI powered by Hybrid RAG · Groq · Tavily Live Web Search · Local Ollama.
          </p>
        </div>
      </div>
      
      {/* Knowledge Domains — consistent borders on all 4 */}
      <div className="grid gap-3.5 sm:grid-cols-2">
        {domains.map((d, idx) => (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.05 }}
            whileHover={{ scale: 1.01, y: -2 }}
            key={d.name}
            className="flex gap-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl shadow-sm hover:shadow-md hover:border-ongc-blue/40 dark:hover:border-blue-500/40 transition-all duration-200 cursor-pointer"
          >
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-50 dark:bg-slate-800 text-ongc-blue dark:text-blue-400 border border-slate-100 dark:border-slate-700">
              {d.icon}
            </div>
            <div>
              <div className="text-xs font-bold text-slate-800 dark:text-white">{d.name}</div>
              <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 leading-snug font-medium">{d.desc}</div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Suggested Prompts */}
      <div className="space-y-3">
        <h3 className="font-bold text-[10px] tracking-widest uppercase text-slate-400 dark:text-slate-500 flex items-center gap-1.5 pl-1">
          <Sparkles size={11} className="text-ongc-blue dark:text-blue-400" />
          Suggested Queries
        </h3>
        <div className="grid gap-3 sm:grid-cols-2">
          {prompts.map((p, idx) => (
            <motion.button
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 + idx * 0.05 }}
              whileHover={{ scale: 1.01, boxShadow: "0 4px 12px rgba(0, 0, 0, 0.04)" }}
              whileTap={{ scale: 0.99 }}
              key={p.text}
              className="flex items-start gap-3 rounded-2xl border border-slate-200/80 bg-white p-4 text-left text-xs font-bold shadow-sm transition-all duration-200 hover:border-ongc-blue hover:text-ongc-blue dark:border-slate-800 dark:bg-slate-900 dark:hover:border-blue-400 dark:hover:text-blue-400"
              onClick={() => onAsk(p.text)}
            >
              {p.icon}
              <span className="leading-relaxed text-slate-700 dark:text-slate-300 font-semibold">{p.text}</span>
            </motion.button>
          ))}
        </div>
      </div>
      
      <div className="flex items-center gap-2 justify-center text-[10px] font-bold text-slate-400 tracking-wide pt-4">
        <Clock size={12} />
        Total queries served on this server: {analytics?.total_questions || 0}
      </div>
    </div>
  );
}

function ResponseLoader({ status = "Thinking..." }) {
  // Simplify status to user-friendly messages
  let displayStatus = "Thinking...";
  
  if (status.includes("Classifying") || status.includes("Routing")) {
    displayStatus = "Thinking...";
  } else if (status.includes("Querying") || status.includes("Retrieving") || status.includes("searching")) {
    if (status.includes("web") || status.includes("Tavily")) {
      displayStatus = "Searching the web...";
    } else if (status.includes("knowledge") || status.includes("KB")) {
      displayStatus = "Searching ONGC Knowledge Base...";
    } else {
      displayStatus = "Searching relevant documents...";
    }
  } else if (status.includes("Synthesizing") || status.includes("Generating")) {
    displayStatus = "Thinking...";
  }

  return (
    <div className="flex justify-start items-start gap-3 w-full max-w-4xl mx-auto">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-tr from-ongc-blue to-ongc-deep text-white shadow-sm">
        <Bot size={18} />
      </div>
      <div className="flex-1">
        <div className="bubble assistant mr-auto bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 shadow-sm rounded-2xl rounded-bl-none max-w-sm">
          <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
            <RefreshCw size={14} className="animate-spin text-ongc-blue" />
            <span>{displayStatus}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function Message({ message, callApi, onRegenerate, isLast, showToast, showTechnical }) {
  const [copied, setCopied] = useState(false);
  const [userFeedback, setUserFeedback] = useState(null);

  async function copyToClipboard() {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      showToast("Copied to clipboard.");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      showToast("Failed to copy.", "error");
    }
  }

  async function vote(helpful) {
    setUserFeedback(helpful ? "like" : "dislike");
    try {
      const res = await callApi("/chat/feedback", "POST", { message_id: message.id, helpful });
      if (res.ok) {
        showToast(helpful ? "Feedback recorded! Thumbs up." : "Feedback recorded! Thumbs down.");
      }
    } catch (e) {
      if (e.message !== "Unauthorized") {
        showToast("Feedback error.", "error");
      }
    }
  }

  function renderSourceBadge() {
    const citationFile = message.citations?.find?.((c) => c.file_name)?.file_name;
    const src = (message.source || "").toLowerCase();
    let label = "";
    let icon = "";
    let badgeClass = "bg-slate-100 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300";

    if (src.includes("focused")) {
      icon = "📄";
      label = citationFile ? `Focused PDF · ${citationFile}` : "Focused PDF";
      badgeClass = "bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300";
    } else if (src.includes("tavily") || src.includes("live web")) {
      icon = "🌐";
      label = "Live Web Search";
      badgeClass = "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300";
    } else if (src.includes("hse")) {
      icon = "🛡️";
      label = "HSE Knowledge Base";
      badgeClass = "bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-300";
    } else if (src.includes("finance")) {
      icon = "💰";
      label = "Finance Knowledge Base";
      badgeClass = "bg-purple-50 dark:bg-purple-950/30 border-purple-200 dark:border-purple-800 text-purple-700 dark:text-purple-300";
    } else if (src.includes("ongc") || src.includes("enterprise") || src.includes("knowledge base")) {
      icon = "🏢";
      label = "ONGC Knowledge Base";
      badgeClass = "bg-slate-100 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300";
    } else if (src.includes("upload")) {
      icon = "📄";
      label = citationFile ? `Uploaded · ${citationFile}` : "Uploaded Document";
      badgeClass = "bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300";
    } else if (src.includes("groq")) {
      icon = "🤖";
      label = "Groq AI";
      badgeClass = "bg-slate-100 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400";
    } else if (src) {
      icon = "ℹ️";
      label = message.source;
    } else {
      return null;
    }

    return (
      <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-semibold shadow-sm shrink-0 ${badgeClass}`}>
        <span className="text-sm leading-none">{icon}</span>
        <span>{label}</span>
      </span>
    );
  }

  const messageVariants = {
    hidden: { opacity: 0, y: 15 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.35, ease: "easeOut" } }
  };

  if (message.role === "user") {
    return (
      <motion.div 
        variants={messageVariants}
        initial="hidden"
        animate="visible"
        className="flex justify-end items-start gap-3 w-full max-w-4xl mx-auto"
      >
        <div className="flex flex-col items-end">
          <div className="bubble user mb-1">
            <div className="prose max-w-none leading-relaxed text-[15px] font-semibold text-white">
              {message.content}
            </div>
          </div>
          
          {/* Timestamp only */}
          <div className="text-[9px] text-slate-400 dark:text-slate-500 mr-2 font-bold justify-end">
            <span>{formatTime(message.created_at)}</span>
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div 
      variants={messageVariants}
      initial="hidden"
      animate="visible"
      className="flex justify-start items-start gap-3 w-full max-w-4xl mx-auto"
    >
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-tr from-ongc-blue to-ongc-deep text-white shadow-sm border border-slate-200/20">
        <Bot size={18} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="bubble assistant mb-1 bg-white dark:bg-slate-900 border border-slate-200/60 dark:border-slate-800/80 shadow-sm w-full">
          <div className="prose dark:prose-invert max-w-none leading-relaxed text-[15px] font-medium text-slate-800 dark:text-slate-100">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            {message.streaming && <span className="stream-cursor" />}
          </div>

          {!message.error && (
            <div className="mt-4 border-t border-slate-200 dark:border-slate-800 pt-3 text-xs text-slate-500 dark:text-slate-400 space-y-3">
              <div className="flex flex-wrap gap-2.5 items-center">
                {renderSourceBadge()}
                {showTechnical && message.response_time_ms !== undefined && message.response_time_ms !== null && (
                  <span className="text-[10px] text-slate-400 font-bold">
                    ({(message.response_time_ms / 1000).toFixed(2)}s latency)
                  </span>
                )}
              </div>

              {/* Display Tavily sources separately */}
              {message.citations?.[0]?.tavily_sources && message.citations[0].tavily_sources.length > 0 && (
                <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800">
                  <div className="font-semibold text-slate-700 dark:text-slate-300 mb-2">Sources:</div>
                  <div className="space-y-1.5">
                    {message.citations[0].tavily_sources.map((source, idx) => (
                      <a
                        key={idx}
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block text-blue-600 dark:text-blue-400 hover:underline truncate"
                      >
                        {source.title}
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* Source Documents — only retrieved chunks that actually contributed to the answer */}
              {(() => {
                const citations = Array.isArray(message.citations) ? message.citations : [];
                const docSources = citations.filter((c) => !c.tavily_sources);
                const seen = new Set();
                const unique = [];
                for (const c of docSources) {
                  if (!c.file_name) continue;
                  const key = `${c.file_name}::${c.page_number ?? ""}`;
                  if (seen.has(key)) continue;
                  seen.add(key);
                  unique.push(c);
                }
                if (unique.length === 0) return null;
                return (
                  <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800 space-y-2">
                    <div className="font-black text-[10px] tracking-widest uppercase text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                      <FileDown size={11} /> Source Documents
                    </div>
                    <div className="space-y-1.5">
                      {unique.map((c, idx) => (
                        <div key={idx} className="flex items-start gap-2.5 rounded-xl bg-blue-50/60 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900/40 px-3 py-2">
                          <FileText size={13} className="text-ongc-blue dark:text-blue-400 shrink-0 mt-0.5" />
                          <div className="min-w-0 flex-1 text-[11px] font-semibold text-slate-700 dark:text-slate-200 leading-snug">
                            <span className="font-black">{c.file_name}</span>
                            {c.page_number !== null && c.page_number !== undefined && (
                              <span className="ml-2 inline-flex items-center rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 px-2 py-0.5 text-[9.5px] text-slate-500 dark:text-slate-400 font-bold">
                                Page {c.page_number}
                              </span>
                            )}
                            {c.similarity_score !== null && c.similarity_score !== undefined && showTechnical && (
                              <span className="ml-2 text-[9.5px] text-slate-400 font-bold">
                                · {(c.similarity_score * 100).toFixed(0)}% match
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })()}

              <div className="flex flex-wrap gap-2 mt-4 pt-3 border-t border-slate-100 dark:border-slate-800">
                <button className={`mini font-bold ${copied ? "text-green-600 border-green-200 bg-green-50 dark:bg-green-955/30" : ""}`} onClick={copyToClipboard}>
                  {copied ? <Check size={11} className="mr-0.5" /> : <Copy size={11} className="mr-0.5" />}
                  {copied ? "Copied" : "Copy"}
                </button>
                
                {isLast && (
                  <button className="mini font-bold hover:text-ongc-blue hover:border-ongc-blue/30" onClick={onRegenerate}>
                    <RefreshCw size={11} className="mr-0.5" />
                    Regenerate
                  </button>
                )}
                
                <button 
                  className={`mini font-bold ${userFeedback === "like" ? "bg-green-50 text-green-700 border-green-300 dark:bg-green-955/30" : ""}`} 
                  onClick={() => vote(true)}
                  title="Helpful"
                >
                  <ThumbsUp size={11} className="mr-0.5" />
                  Helpful
                </button>
                
                <button 
                  className={`mini font-bold ${userFeedback === "dislike" ? "bg-red-50 text-red-700 border-red-300 dark:bg-red-955/30" : ""}`} 
                  onClick={() => vote(false)}
                  title="Not helpful"
                >
                  <ThumbsDown size={11} className="mr-0.5" />
                  Not Helpful
                </button>
              </div>
            </div>
          )}
        </div>
        <div className="text-[9px] text-slate-400 dark:text-slate-500 ml-2 flex items-center gap-1 font-bold">
          <Clock size={9} />
          {formatTime(message.created_at)}
        </div>
      </div>
    </motion.div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-3.5 shadow-sm dark:bg-slate-900 transition-colors">
      <div className="text-[9px] font-bold tracking-widest uppercase text-slate-400">{label}</div>
      <div className="text-base font-black text-slate-800 dark:text-white mt-1">{value}</div>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
