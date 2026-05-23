import { API } from "../config/api";

const CHAT_API = `${API.chat}/`;
const STORAGE_KEY = "chatBackgroundState";
const UPDATE_EVENT = "chat-bg-updated";
let reloadHandled = false;

function readState() {
  if (!reloadHandled) {
    reloadHandled = true;
    try {
      const nav = performance.getEntriesByType("navigation");
      const hardReload =
        (nav && nav[0] && nav[0].type === "reload") ||
        (performance.navigation && performance.navigation.type === 1);
      if (hardReload) {
        localStorage.removeItem(STORAGE_KEY);
      }
    } catch {
      // ignore
    }
  }

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    if (!parsed || !Array.isArray(parsed.messages)) {
      return { messages: [], loading: false, error: null };
    }
    const state = {
      messages: parsed.messages,
      loading: Boolean(parsed.loading),
      error: parsed.error || null,
    };
    // Prevent stuck spinner after hard refresh (silently)
    if (state.loading) {
      state.loading = false;
      state.error = null;
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    }
    return state;
  } catch {
    return { messages: [], loading: false, error: null };
  }
}

function writeState(next) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  window.dispatchEvent(new CustomEvent(UPDATE_EVENT));
}

export function getChatState() {
  return readState();
}

export function subscribeChatUpdates(callback) {
  const handler = () => callback(readState());
  window.addEventListener(UPDATE_EVENT, handler);
  return () => window.removeEventListener(UPDATE_EVENT, handler);
}

export function startChatMessage(text) {
  const current = readState();
  const userMsg = { role: "user", content: text };
  writeState({
    ...current,
    messages: [...current.messages, userMsg],
    loading: true,
    error: null,
  });

  (async () => {
    const snapshot = readState();
    try {
      const history = snapshot.messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));
      const res = await fetch(CHAT_API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.message || `Request failed: ${res.status}`);

      const latest = readState();
      writeState({
        ...latest,
        messages: [...latest.messages, { role: "assistant", content: data.reply ?? "No response." }],
        loading: false,
        error: null,
      });
    } catch (err) {
      const latest = readState();
      const msg = err?.message || "Something went wrong.";
      writeState({
        ...latest,
        messages: [...latest.messages, { role: "assistant", content: `Error: ${msg}` }],
        loading: false,
        error: msg,
      });
    }
  })();
}

