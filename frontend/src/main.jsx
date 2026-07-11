import React, { useEffect, useMemo, useState, useRef } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { createRoot } from "react-dom/client";
import ReactMarkdown from "react-markdown";
import { AlertCircle, Bot, Check, Clock, Copy, Download, Eye, EyeOff, File, FileText, Focus, LogOut, Menu, Moon, Pin, Plus, RefreshCw, Search, Send, Sun, ThumbsDown, ThumbsUp, Trash2, Upload, X } from "lucide-react";
import "./styles.css";

const API = import.meta.env.VITE_API_URL || (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" ? "http://localhost:8000/api" : `${window.location.origin}/api`);

function storedTokens() {
  try {
    // Authentication intentionally lasts only for the active browser session.
    // A newly opened browser/application session must start at Login.
    return JSON.parse(sessionStorage.getItem("tokens") || "null");
  } catch {
    sessionStorage.removeItem("tokens");
    return null;
  }
}

function ongcLogo() {
  return (
    <div className="flex h-11 w-11 items-center justify-center rounded-md bg-white shadow-sm transition hover:scale-105">
      <div className="text-center text-[10px] font-black leading-3 text-ongc-blue">
        ONGC
        <div className="mx-auto mt-0.5 h-1 w-6 rounded-full bg-ongc-red" />
      </div>
    </div>
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
    const d = new Date(isoString);
    return d.toLocaleDateString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

function formatTime(isoString) {
  if (!isoString) return "";
  try {
    const d = new Date(isoString);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

function ProtectedRoute({ children, tokens, authChecked }) {
  const location = useLocation();

  if (!authChecked) {
    return (
      <main className="grid min-h-screen place-items-center bg-slate-100 text-slate-600 dark:bg-slate-950 dark:text-slate-300">
        <div className="rounded-xl border border-slate-200 bg-white px-5 py-4 text-sm font-semibold shadow-sm dark:border-slate-800 dark:bg-slate-900">
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
      <main className="grid min-h-screen place-items-center bg-slate-100 text-slate-600 dark:bg-slate-950 dark:text-slate-300">
        <div className="rounded-xl border border-slate-200 bg-white px-5 py-4 text-sm font-semibold shadow-sm dark:border-slate-800 dark:bg-slate-900">
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
    return localStorage.getItem("theme") === "dark";
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
        // Never grant dashboard access without a successful backend validation.
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
    // Clear keys created by earlier versions before routing away from Dashboard.
    localStorage.removeItem("tokens");
    localStorage.removeItem("active_session_id");
    localStorage.removeItem("focusDocumentId");
    setAuth(null);
  };

  const tokens = auth?.tokens || null;

  return (
    <BrowserRouter>
      <Routes>
        {/* Protected Dashboard/Chat Routes */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute tokens={tokens} authChecked={authChecked}>
              <Dashboard key={auth?.user?.id ?? "unauthenticated"} tokens={tokens} user={auth?.user} onLogout={handleLogout} dark={dark} setDark={setDark} />
            </ProtectedRoute>
          }
        />
        {/* Alias routes that point to the Dashboard */}
        <Route path="/chat" element={<Navigate to="/dashboard" replace />} />
        <Route path="/history" element={<Navigate to="/dashboard" replace />} />
        <Route path="/settings" element={<Navigate to="/dashboard" replace />} />
        <Route path="/uploads" element={<Navigate to="/dashboard" replace />} />
        <Route path="/analytics" element={<Navigate to="/dashboard" replace />} />

        {/* Public Login Route */}
        <Route
          path="/login"
          element={
            <PublicRoute tokens={tokens} authChecked={authChecked}>
              <Login onLogin={setAuth} dark={dark} setDark={setDark} />
            </PublicRoute>
          }
        />

        {/* Catch-all Redirect */}
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
      if (!res.ok) {
        setError((await res.json()).detail || "Unable to continue");
        return;
      }
      if (mode === "register") {
        setMode("login");
        return;
      }
      const data = await res.json();
      const me = await fetch(`${API}/auth/me`, { headers: { Authorization: `Bearer ${data.access_token}` } });
      if (!me.ok) throw new Error("Authentication validation failed");
      sessionStorage.setItem("tokens", JSON.stringify(data));
      onLogin({ tokens: data, user: await me.json() });
    } catch {
      setError("Network error. Backend server is unreachable.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950 dark:bg-slate-950 dark:text-white transition-colors duration-300">
      <div className="mx-auto grid min-h-screen max-w-6xl grid-cols-1 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="flex flex-col justify-between bg-ongc-blue p-8 text-white lg:p-12 relative overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_30%,#08345f,transparent)] opacity-40" />
          <div className="flex items-center gap-3 relative z-10">
            {ongcLogo()}
            <div>
              <h1 className="text-3xl font-bold tracking-normal">ONGC IntelliAssist</h1>
              <p className="text-sm text-blue-100">Hybrid Enterprise AI Knowledge Assistant</p>
            </div>
          </div>
          <div className="max-w-2xl py-16 relative z-10">
            <p className="text-lg text-blue-50 leading-relaxed">
              Ask questions across uploaded documents, policies, the built-in enterprise knowledge base, and local AI fallback. Features automatic routing, persistent context switching, and attribution.
            </p>
            <div className="mt-8 grid grid-cols-3 gap-3 text-sm font-medium">
              <div className="rounded-lg bg-white/10 backdrop-blur-sm p-4 border border-white/10 transition hover:bg-white/15">Multi-Document RAG</div>
              <div className="rounded-lg bg-white/10 backdrop-blur-sm p-4 border border-white/10 transition hover:bg-white/15">Enterprise KB</div>
              <div className="rounded-lg bg-white/10 backdrop-blur-sm p-4 border border-white/10 transition hover:bg-white/15">Local Llama Fallback</div>
            </div>
          </div>
          <p className="text-xs text-blue-200 relative z-10">Secure enterprise agent environment conforming to ONGC internal security regulations.</p>
        </section>
        <section className="flex items-center justify-center p-6 bg-slate-50 dark:bg-slate-950 transition-colors duration-300">
          <form onSubmit={submit} className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-8 shadow-md dark:border-slate-800 dark:bg-slate-900 transition-all duration-200 space-y-4">
            <div>
              <div className="mb-6 flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold tracking-tight">{mode === "login" ? "Sign in" : "Create account"}</h2>
                  <p className="text-sm text-slate-500 dark:text-slate-400">JWT-secured corporate gateway</p>
                </div>
                <button type="button" className="icon-btn" onClick={() => setDark(!dark)} title={dark ? "Switch to light mode" : "Switch to dark mode"}>
                  {dark ? <Sun size={18} /> : <Moon size={18} />}
                </button>
              </div>
            </div>
            {mode === "register" && <input className="field mb-0" placeholder="Full name" value={name} onChange={(e) => setName(e.target.value)} />}
            <input className="field mb-0" type="email" required autoComplete="email" placeholder="Email address" value={email} onChange={(e) => setEmail(e.target.value)} />
            <div className="relative">
              <input
                className="field pr-10 mb-0"
                placeholder="Password (Admin@12345)"
                type={showPassword ? "text" : "password"}
                required
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <button
                type="button"
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            {error && (
              <p className="rounded-lg bg-red-50 dark:bg-red-950/30 p-3 text-sm text-red-700 dark:text-red-300 border border-red-200 dark:border-red-900 flex items-center gap-2">
                <AlertCircle size={16} />
                {error}
              </p>
            )}
            <button disabled={loading} className="primary w-full h-11 text-base shadow-sm hover:shadow disabled:opacity-60">{loading ? "Authenticating..." : mode === "login" ? "Login" : "Register"}</button>
            <button type="button" className="mt-4 w-full text-sm font-semibold text-ongc-blue dark:text-blue-400 hover:underline" onClick={() => setMode(mode === "login" ? "register" : "login")}>
              {mode === "login" ? "Register new employee" : "Back to login"}
            </button>
          </form>
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
  const [loading, setLoading] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState("Thinking...");
  const [uploading, setUploading] = useState(false);
  const [toasts, setToasts] = useState([]);
  const [focusDocumentId, setFocusDocumentId] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    const saved = localStorage.getItem("sidebar_open");
    return saved !== null ? saved === "true" : true;
  });
  const [developerMode, setDeveloperMode] = useState(() => localStorage.getItem("developerMode") === "true");
  const [showScrollButton, setShowScrollButton] = useState(false);
  
  const chatContainerRef = useRef(null);
  const requestControllerRef = useRef(null);
  const focusDoc = useMemo(() => docs.find((d) => d.id === focusDocumentId) || null, [docs, focusDocumentId]);

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

  // The route unmounts on logout/user change. Abort ongoing reads so no late
  // response can update a newly authenticated user's interface.
  useEffect(() => () => requestControllerRef.current?.abort(), []);

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

  // Helper function to call the api, automatically handling headers and 401 redirection
  async function callApi(path, method = "GET", body = null, isMultipart = false, signal = undefined) {
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
    const res = await fetch(`${API}${path}`, opts);
    if (res.status === 401) {
      onLogout();
      throw new Error("Unauthorized");
    }
    return res;
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
    requestControllerRef.current?.abort();
    requestControllerRef.current = controller;
    try {
      const [s, d, a] = await Promise.all([
        callApi("/chat/sessions", "GET", null, false, controller.signal).then((r) => r.ok ? r.json() : []),
        callApi("/documents", "GET", null, false, controller.signal).then((r) => r.ok ? r.json() : []),
        callApi(analyticsPath(), "GET", null, false, controller.signal).then((r) => r.ok ? r.json() : null)
      ]);
      setSessions(Array.isArray(s) ? s : []);
      setDocs(Array.isArray(d) ? d : []);
      setAnalytics(a);
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
    setShowScrollButton(!isNearBottom);
  };

  useEffect(() => {
    if (messages.length === 0) return;
    const lastMessage = messages[messages.length - 1];
    if (lastMessage.role === "user") {
      scrollToBottom("smooth");
    } else {
      const container = chatContainerRef.current;
      if (container) {
        const threshold = 250;
        const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < threshold;
        if (isNearBottom) {
          scrollToBottom("smooth");
        }
      }
    }
  }, [messages, loading]);

  async function openSession(id, refreshAnalytics = true) {
    setSessionId(id);
    sessionStorage.setItem(`active_session_id_${user.id}`, id);
    setFocusDocumentId(null);
    try {
      const data = await callApi(`/chat/sessions/${id}/messages`).then((r) => r.json());
      setMessages(Array.isArray(data) ? data : []);
      if (refreshAnalytics) {
        const a = await callApi(analyticsPath(id)).then((r) => r.ok ? r.json() : null);
        setAnalytics(a);
      }
      setTimeout(() => scrollToBottom("auto"), 50);
    } catch (e) {
      if (e.message !== "Unauthorized") {
        showToast("Failed to retrieve chat messages.", "error");
      }
    }
  }

  async function send(text = question) {
    if (!text.trim()) return;
    setLoading(true);
    setLoadingStatus("Thinking...");
    const localQuestion = text;
    requestControllerRef.current?.abort();
    const controller = new AbortController();
    requestControllerRef.current = controller;
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
          response_time_ms: 0,
          citations: [],
          created_at: new Date().toISOString()
        }]);
        setLoading(false);
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

          if (event.event === "meta") {
            setSessionId(event.session_id);
            sessionStorage.setItem(`active_session_id_${user.id}`, event.session_id);
          }

          if (event.event === "token") {
            if (!assistantStarted) {
              assistantStarted = true;
              setLoading(false);
              setMessages((old) => [...old, {
                id: assistantTempId,
                role: "assistant",
                content: event.text || "",
                source: "General AI",
                domain: null,
                response_time_ms: null,
                citations: [],
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
                    citations: event.citations || []
                  }
                : m
            )));
          }
        }
      }
    } catch (e) {
      if (e.name !== "AbortError" && e.message !== "Unauthorized") {
        setMessages((old) => [...old, {
          id: `e-${Date.now()}`,
          role: "assistant",
          content: "Request timeout or server connection lost.",
          source: "Network Error",
          domain: "Error",
          response_time_ms: 0,
          citations: [],
          created_at: new Date().toISOString()
        }]);
      }
    } finally {
      setLoading(false);
      setLoadingStatus("Thinking...");
      load();
    }
  }

  function startNewChat() {
    setSessionId(null);
    sessionStorage.removeItem(`active_session_id_${user.id}`);
    setFocusDocumentId(null);
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
    setUploading(true);
    showToast("Processing document. Extracting text & calculating embeddings...");
    const form = new FormData();
    for (const file of event.target.files) form.append("files", file);
    try {
      const res = await callApi("/documents", "POST", form, true);
      if (res.ok) {
        showToast("Documents uploaded and indexed successfully!");
      } else {
        const err = await res.json().catch(() => ({}));
        showToast(err.detail || "Upload failed.", "error");
      }
    } catch (e) {
      if (e.message !== "Unauthorized") {
        showToast("Network upload error.", "error");
      }
    } finally {
      setUploading(false);
      event.target.value = "";
      load();
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

  return (
    <main className="flex h-screen w-screen bg-slate-100 text-slate-950 dark:bg-slate-950 dark:text-slate-100 transition-colors duration-300 relative overflow-hidden">
      {/* Toast Notification HUD */}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((t) => (
          <div key={t.id} className={`toast-animate flex items-center gap-2 rounded-lg px-4 py-3 text-sm font-semibold shadow-lg text-white ${t.type === "error" ? "bg-red-600" : "bg-ongc-blue"}`}>
            <AlertCircle size={16} />
            {t.message}
          </div>
        ))}
      </div>

      {/* Mobile Sidebar backdrop overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 z-40 bg-black/40 md:hidden" 
          onClick={() => toggleSidebar(false)} 
        />
      )}

      {/* Left Sidebar */}
      <aside className={`${sidebarOpen ? "fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 md:static md:flex md:w-80" : "hidden"} transition-all duration-300 h-full shrink-0 overflow-hidden`}>
        <div className="flex items-center gap-3 border-b border-slate-200 p-4 dark:border-slate-800 shrink-0">
          {ongcLogo()}
          <div className="min-w-0 flex-1">
            <h1 className="font-bold text-base text-slate-950 dark:text-white">ONGC IntelliAssist</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">Enterprise Chat Environment</p>
          </div>
          <button className="icon-btn h-9 w-9" onClick={() => toggleSidebar(false)} title="Collapse sidebar">
            <X size={17} />
          </button>
        </div>
        <div className="p-4 flex flex-col gap-2.5 shrink-0 border-b border-slate-100 dark:border-slate-800/60">
          <button className="primary w-full h-10 shadow-sm" onClick={startNewChat} title="Start a fresh chat">
            <Plus size={16} />New Chat
          </button>
          
          <label className="flex h-10 cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-sm font-medium text-slate-600 dark:text-slate-300 transition hover:bg-slate-100 dark:hover:bg-slate-900">
            <Upload size={16} />
            {uploading ? "Indexing File..." : "Upload Documents"}
            <input multiple type="file" className="hidden" accept=".pdf,.docx,.txt" onChange={upload} disabled={uploading} />
          </label>
          
          <div className="flex items-center gap-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 transition focus-within:border-ongc-blue">
            <Search className="text-slate-400" size={16} />
            <input className="h-9 flex-1 bg-transparent text-sm outline-none text-slate-850 dark:text-slate-100" placeholder="Search chats..." value={query} onChange={(e) => setQuery(e.target.value)} />
          </div>
        </div>

        {/* Sessions List - scroll independently */}
        <div className="flex-1 overflow-y-auto px-3 py-3 custom-scrollbar space-y-4">
          {filteredSessions.length === 0 ? (
            <p className="text-center text-xs text-slate-400 mt-4">No chats found</p>
          ) : (
            (() => {
              const groups = groupSessions(filteredSessions);
              const renderSection = (title, items) => {
                if (items.length === 0) return null;
                return (
                  <div key={title} className="space-y-1">
                    <h3 className="px-2 text-[10px] font-bold tracking-wider uppercase text-slate-400 dark:text-slate-500">{title}</h3>
                    {items.map((s) => (
                      <div key={s.id} className={`group mb-1 flex items-center gap-1 rounded-lg p-2 transition-all-200 ${sessionId === s.id ? "bg-blue-50/80 text-ongc-blue dark:bg-blue-950/40 dark:text-blue-300 font-semibold" : "hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-350"}`}>
                        <button onClick={() => { openSession(s.id); if(window.innerWidth < 768) toggleSidebar(false); }} className="min-w-0 flex-1 truncate text-left text-sm" title={s.title}>
                          {s.title}
                        </button>
                        <div className="flex opacity-0 group-hover:opacity-100 transition-opacity">
                          <button className={`mini-icon ${s.pinned ? "text-amber-500 opacity-100" : ""}`} onClick={(e) => togglePin(s.id, e)} title={s.pinned ? "Unpin chat" : "Pin chat"}>
                            <Pin size={13} className={s.pinned ? "fill-amber-500" : ""} />
                          </button>
                          <button className="mini-icon" onClick={() => renameSession(s.id, s.title)} title="Rename chat">
                            <FileText size={13} />
                          </button>
                          <button className="mini-icon hover:text-red-500" onClick={(e) => deleteSession(s.id, e)} title="Delete chat">
                            <Trash2 size={13} />
                          </button>
                        </div>
                        {s.pinned && <Pin size={11} className="text-amber-500 fill-amber-500 ml-1 group-hover:hidden" />}
                      </div>
                    ))}
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
        <div className="border-t border-slate-200 dark:border-slate-800 p-4 text-xs font-semibold text-slate-500 flex items-center gap-2 shrink-0">
          <File size={13} />
          Total Files Indexed: {docs.length}
        </div>
      </aside>

      {/* Main chat layout */}
      <section className="flex min-w-0 flex-1 flex-col h-full overflow-hidden transition-colors duration-300">
        <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-6 dark:border-slate-800 dark:bg-slate-900 transition-colors duration-300 shrink-0">
          <div className="flex items-center gap-3">
            {!sidebarOpen && (
              <button className="icon-btn h-9 w-9" onClick={() => toggleSidebar(true)} title="Open sidebar">
                <Menu size={17} />
              </button>
            )}
            <Bot className="text-ongc-blue dark:text-blue-400" />
            <div>
              <h2 className="font-bold text-base text-slate-950 dark:text-white">ONGC IntelliAssist</h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">Ask naturally. The assistant selects the right knowledge source silently.</p>
            </div>
          </div>
          <div className="flex gap-2">
            <button className="icon-btn" onClick={exportChat} title="Export current chat">
              <Download size={18} />
            </button>
            <button className="icon-btn" onClick={() => setDark(!dark)} title={dark ? "Switch to light theme" : "Switch to dark theme"}>
              {dark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <button className="icon-btn hover:bg-red-50 dark:hover:bg-red-900 hover:text-red-600 dark:hover:text-red-300" onClick={onLogout} title="Logout">
              <LogOut size={18} />
            </button>
          </div>
        </header>

        {/* Dashboard Grid layout */}
        <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[1fr_320px] overflow-hidden">
          <div className="flex min-w-0 flex-col h-full overflow-hidden relative">
            
            {/* Scrollable chat body */}
            <div 
              ref={chatContainerRef}
              onScroll={handleScroll}
              className="flex-1 overflow-y-auto p-4 md:p-6 space-y-5 bg-slate-50 dark:bg-slate-950 custom-scrollbar"
            >
              {messages.length === 0 ? (
                <Welcome analytics={analytics} onAsk={send} />
              ) : (
                messages.map((m) => (
                  <Message 
                    key={m.id} 
                    message={m} 
                    callApi={callApi}
                    onRegenerate={regenerate} 
                    isLast={messages[messages.length - 1].id === m.id} 
                    showToast={showToast} 
                  />
                ))
              )}
              {loading && <ResponseLoader />}
            </div>

            {/* Smart Scroll: floating button */}
            {showScrollButton && (
              <button
                onClick={() => {
                  scrollToBottom("smooth");
                  setShowScrollButton(false);
                }}
                className="absolute bottom-24 left-1/2 -translate-x-1/2 z-35 flex items-center gap-1.5 rounded-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 px-4 py-2.5 text-xs font-bold shadow-md text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 hover:scale-105 active:scale-[0.98] transition-all duration-200"
              >
                <span>⬇</span> Jump to latest
              </button>
            )}

            {/* Fixed input area */}
            <div className="border-t border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 transition-colors duration-300 shrink-0">
              <div className="max-w-5xl mx-auto space-y-2">
                {focusDoc && (
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-ongc-blue/10 dark:bg-blue-900/30 border border-ongc-blue/30 dark:border-blue-700 px-3 py-1 text-xs font-semibold text-ongc-blue dark:text-blue-300">
                      <Focus size={11} />
                      Focus: {focusDoc.filename}
                    </span>
                    <button
                      className="inline-flex items-center gap-1 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 px-2.5 py-1 text-xs font-medium text-slate-500 dark:text-slate-400 hover:text-red-500 hover:border-red-200 dark:hover:border-red-800 transition"
                      onClick={exitFocusMode}
                      title="Exit Focus Mode"
                    >
                      <X size={11} /> Exit Focus
                    </button>
                  </div>
                )}
                <div className="flex gap-2.5">
                  <textarea
                    className="min-h-[48px] max-h-40 flex-1 resize-none rounded-lg border border-slate-300 bg-slate-50 p-3 text-sm text-slate-800 dark:text-slate-100 outline-none focus:border-ongc-blue focus:bg-white dark:border-slate-700 dark:bg-slate-950 dark:focus:border-blue-500"
                    placeholder="Ask about corporate policies, safety manuals, exploration SOPs…"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
                  />
                  <button className="primary self-end h-11 px-5 shadow hover:bg-ongc-deep transition" onClick={() => send()} disabled={loading}>
                    <Send size={16} />Send
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Right Sidebar - Fixed metrics on top, documents scroll independently */}
          <aside className="hidden w-[320px] flex-col h-full border-l border-slate-200 bg-slate-50/50 p-6 dark:border-slate-800 dark:bg-slate-900/60 lg:flex transition-colors duration-300 overflow-hidden shrink-0">
            <h3 className="mb-4 font-bold text-sm tracking-wider uppercase text-slate-500 dark:text-slate-400 shrink-0">Context Analytics</h3>
            <div className="grid grid-cols-2 gap-3 mb-6 shrink-0">
              <Metric label="Total Chats" value={analytics?.total_chats ?? 0} />
              <Metric label="Questions Answered" value={analytics?.questions_answered ?? 0} />
              <Metric label="Average latency" value={`${analytics?.average_response_time_ms ? (analytics.average_response_time_ms / 1000).toFixed(1) : 0}s`} />
              <Metric label="RAG Hits" value={analytics?.rag_queries ?? 0} />
              <Metric label="KB Hits" value={analytics?.kb_queries ?? 0} />
              <Metric label="Fallback LLM" value={analytics?.fallback_queries ?? 0} />
            </div>

            {developerMode && analytics?.current_retrieval_source && (
              <div className="mb-6 p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-3 shrink-0">
                <h4 className="font-bold text-xs tracking-wider uppercase text-slate-500 dark:text-slate-400">Current Session Routing</h4>
                <div>
                  <div className="text-[10px] font-medium text-slate-400">ACTIVE SOURCE</div>
                  <div className="text-sm font-bold text-ongc-blue dark:text-blue-400">{analytics?.current_retrieval_source || "None"}</div>
                </div>
                <div>
                  <div className="text-[10px] font-medium text-slate-400">FOCUS DOCUMENT</div>
                  <div className="text-sm font-bold text-slate-700 dark:text-slate-300 truncate" title={analytics?.active_document}>{analytics?.active_document || "None"}</div>
                </div>
              </div>
            )}

            <h3 className="mb-4 font-bold text-sm tracking-wider uppercase text-slate-500 dark:text-slate-400 shrink-0">Uploaded Library</h3>
            <div className="flex-1 overflow-y-auto space-y-2.5 custom-scrollbar pr-1">
              {docs.length === 0 ? (
                <p className="text-xs text-slate-400 italic">No custom document files uploaded yet.</p>
              ) : (
                docs.map((doc) => {
                  const isFocused = focusDocumentId === doc.id;
                  return (
                    <div key={doc.id} className={`group relative flex flex-col gap-1.5 rounded-xl border bg-white p-3.5 dark:bg-slate-900 shadow-sm transition hover:border-ongc-blue/40 ${isFocused ? "border-ongc-blue dark:border-blue-500" : "border-slate-200 dark:border-slate-800"}`}>
                      <div className="flex items-start gap-2.5">
                        <FileText size={18} className={`shrink-0 mt-0.5 ${isFocused ? "text-ongc-blue dark:text-blue-400" : "text-slate-400"}`} />
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-sm font-semibold text-slate-800 dark:text-slate-100" title={doc.filename}>{doc.filename}</div>
                          <div className="flex flex-wrap gap-x-2 text-[10px] text-slate-400 mt-1">
                            <span>{formatBytes(doc.size_bytes)}</span>
                            <span>•</span>
                            <span>{formatDate(doc.created_at)}</span>
                          </div>
                        </div>
                        <button className="text-slate-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity shrink-0 mr-2" onClick={(e) => deleteDoc(doc, e)} title="Delete document">
                          <Trash2 size={15} />
                        </button>
                        <button className="text-slate-400 hover:text-ongc-blue opacity-0 group-hover:opacity-100 transition-opacity shrink-0" onClick={(e) => toggleDoc(doc.id, e)} title={doc.enabled ? "Disable document" : "Enable document"}>
                          {doc.enabled ? <Check size={15} /> : <Clock size={15} />}
                        </button>
                      </div>
                      <div className="flex items-center gap-1.5 mt-1 border-t border-slate-100 dark:border-slate-800 pt-1.5 justify-between">
                        <span className="text-[9px] uppercase tracking-wider font-extrabold text-slate-400">STATUS</span>
                        <span className="inline-flex items-center rounded-full bg-green-50 dark:bg-green-950/30 px-2 py-0.5 text-[10px] font-medium text-green-700 dark:text-green-400 border border-green-200 dark:border-green-900">
                          {doc.status || "Indexed"}
                        </span>
                        <button
                          onClick={() => isFocused ? exitFocusMode() : enterFocusMode(doc.id)}
                          className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold border transition ${
                            isFocused
                              ? "bg-ongc-blue text-white border-ongc-blue"
                              : "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-700 hover:border-ongc-blue/50 hover:text-ongc-blue"
                          }`}
                          title={isFocused ? "Exit Focus Mode" : "Focus on this document"}
                        >
                          <Focus size={9} />
                          {isFocused ? "Focused" : "Focus"}
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}

function Welcome({ analytics, onAsk }) {
  const prompts = [
    { icon: "🛢", text: "Explain ONGC exploration workflow" },
    { icon: "🦺", text: "What are the PPE requirements?" },
    { icon: "📑", text: "Summarize my uploaded document" },
    { icon: "👨💼", text: "Explain ONGC HR leave policy" },
    { icon: "💰", text: "Explain procurement process" },
    { icon: "⚙", text: "What is reservoir engineering?" }
  ];
  return (
    <div className="mx-auto max-w-2xl py-8 md:py-12 space-y-6 text-slate-800 dark:text-slate-200">
      <div className="text-center space-y-3">
        <h2 className="text-3xl font-black tracking-tight text-slate-900 dark:text-white flex flex-col items-center justify-center gap-2">
          <span className="text-4xl leading-none">👋</span>
          <span>Welcome to ONGC IntelliAssist</span>
        </h2>
        <p className="text-base text-slate-500 dark:text-slate-400 max-w-lg mx-auto">
          Your AI-powered enterprise assistant.
        </p>
      </div>
      
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm">
        <h3 className="font-bold text-xs tracking-wider uppercase text-slate-500 dark:text-slate-450 mb-3">You can ask about:</h3>
        <ul className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm text-slate-650 dark:text-slate-350">
          <li className="flex items-center gap-1.5">🔹 ONGC Operations</li>
          <li className="flex items-center gap-1.5">🔹 Exploration & Drilling</li>
          <li className="flex items-center gap-1.5">🔹 HR Policies</li>
          <li className="flex items-center gap-1.5">🔹 Finance</li>
          <li className="flex items-center gap-1.5">🔹 Procurement</li>
          <li className="flex items-center gap-1.5">🔹 HSE & Safety</li>
          <li className="flex items-center gap-1.5">🔹 Uploaded Documents</li>
          <li className="flex items-center gap-1.5">🔹 General Knowledge</li>
        </ul>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {prompts.map((p) => (
          <button
            key={p.text}
            className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-4 text-left text-sm font-medium shadow-sm transition hover:border-ongc-blue hover:text-ongc-blue dark:border-slate-800 dark:bg-slate-900 dark:hover:border-blue-500 dark:hover:text-blue-400 hover:scale-[1.01] hover:shadow duration-150"
            onClick={() => onAsk(p.text)}
          >
            <span className="text-lg shrink-0 leading-none">{p.icon}</span>
            <span className="leading-snug text-slate-800 dark:text-slate-200">{p.text}</span>
          </button>
        ))}
      </div>
      
      <div className="flex items-center gap-2 justify-center text-xs font-semibold text-slate-400 pt-2">
        <Clock size={14} />
        Total queries served on this server: {analytics?.total_questions || 0}
      </div>
    </div>
  );
}

function ResponseLoader() {
  const [progressStep, setProgressStep] = useState(0);
  const steps = [
    "Thinking...",
    "Searching knowledge base...",
    "Generating response..."
  ];

  useEffect(() => {
    const timer = setInterval(() => {
      setProgressStep((prev) => (prev < steps.length - 1 ? prev + 1 : prev));
    }, 1500);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="bubble assistant mr-auto flex flex-col gap-2 border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 shadow-sm rounded-2xl rounded-bl-none max-w-[85%] md:max-w-[75%] transition-all duration-300">
      <div className="flex items-center gap-3 text-sm font-semibold text-slate-600 dark:text-slate-400">
        <div className="flex space-x-1.5 items-center">
          <div className="w-2.5 h-2.5 rounded-full bg-ongc-blue dark:bg-blue-400 animate-bounce" style={{ animationDelay: "0ms" }} />
          <div className="w-2.5 h-2.5 rounded-full bg-ongc-blue dark:bg-blue-400 animate-bounce" style={{ animationDelay: "150ms" }} />
          <div className="w-2.5 h-2.5 rounded-full bg-ongc-blue dark:bg-blue-400 animate-bounce" style={{ animationDelay: "300ms" }} />
        </div>
        <span>{steps[progressStep]}</span>
      </div>
    </div>
  );
}

function Message({ message, callApi, onRegenerate, isLast, showToast }) {
  const [copied, setCopied] = useState(false);
  const [userFeedback, setUserFeedback] = useState(null); // 'like' or 'dislike'

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
        showToast(helpful ? "Feedback submitted! Thumbs up recorded." : "Feedback submitted! Thumbs down recorded.");
      }
    } catch (e) {
      if (e.message !== "Unauthorized") {
        showToast("Feedback error.", "error");
      }
    }
  }

  function renderSourceBadge() {
    const citationFile = message.citations?.find?.((c) => c.file_name)?.file_name;
    let label = message.source || "General AI";
    let icon = "🧠";

    if (label === "General AI") {
      label = "General AI";
      icon = "🧠";
    } else if (label === "Uploaded Documents") {
      label = citationFile || "Uploaded Document";
      icon = "📚";
    } else if (label === "ONGC Knowledge Base") {
      label = "ONGC Knowledge Base";
      icon = "🏢";
    } else if (label === "Enterprise Knowledge Base") {
      label = "Enterprise Knowledge Base";
      icon = "📄";
    } else {
      label = citationFile || label;
      icon = "📄";
    }

    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-300 shadow-sm shrink-0">
        <span>{icon}</span>
        <span>{label}</span>
      </span>
    );
  }

  return (
    <article className={`bubble relative group ${message.role === "assistant" ? "assistant mr-auto border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900" : "user ml-auto bg-ongc-blue text-white"}`}>
      <div className={`text-[10px] absolute top-2.5 right-3 flex items-center gap-1 ${message.role === "user" ? "text-blue-100" : "text-slate-400 dark:text-slate-500"}`}>
        <Clock size={10} />
        {formatTime(message.created_at)}
      </div>

      <div className={`prose dark:prose-invert max-w-none leading-relaxed text-[15px] ${message.role === "user" ? "prose-user text-white" : "text-slate-850 dark:text-slate-100"}`}>
        <ReactMarkdown>{message.content}</ReactMarkdown>
      </div>

      {message.role === "assistant" && (
        <div className="mt-4 border-t border-slate-200 dark:border-slate-800 pt-3 text-xs text-slate-500 dark:text-slate-400 space-y-3">
          <div className="flex flex-wrap gap-2.5 items-center">
            {renderSourceBadge()}
            {message.response_time_ms !== undefined && message.response_time_ms !== null && (
              <span className="text-[10px] text-slate-400">
                ({(message.response_time_ms / 1000).toFixed(2)}s latency)
              </span>
            )}
          </div>

          {/* Clean Action Row */}
          <div className="flex flex-wrap gap-2 mt-4 pt-3 border-t border-slate-800 dark:border-slate-800">
            <button className={`mini ${copied ? "text-green-600 border-green-200 bg-green-50 dark:bg-green-950/30" : ""}`} onClick={copyToClipboard}>
              {copied ? "✔ Copied" : "📋 Copy"}
            </button>
            
            {isLast && (
              <button className="mini hover:text-ongc-blue hover:border-ongc-blue/30" onClick={onRegenerate}>
                🔄 Regenerate
              </button>
            )}
            
            <button 
              className={`mini ${userFeedback === "like" ? "bg-green-50 text-green-700 border-green-300 dark:bg-green-950/30" : ""}`} 
              onClick={() => vote(true)}
              title="Helpful (thumbs up)"
            >
              👍 Helpful
            </button>
            
            <button 
              className={`mini ${userFeedback === "dislike" ? "bg-red-50 text-red-700 border-red-300 dark:bg-red-950/30" : ""}`} 
              onClick={() => vote(false)}
              title="Not helpful (thumbs down)"
            >
              👎 Not Helpful
            </button>
          </div>
        </div>
      )}
    </article>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white p-3.5 shadow-sm dark:bg-slate-900 transition-colors">
      <div className="text-[10px] font-bold tracking-wider uppercase text-slate-400">{label}</div>
      <div className="text-lg font-black text-slate-850 dark:text-white mt-1">{value}</div>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
