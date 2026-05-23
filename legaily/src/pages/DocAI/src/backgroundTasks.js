import { processFile, translateFile } from "./api";

const STORAGE_KEY = "docaiBackgroundTasks";
const UPDATE_EVENT = "docai-task-updated";
let reloadHandled = false;

function readTasks() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeTasks(tasks) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
  window.dispatchEvent(new CustomEvent(UPDATE_EVENT));
}

function isHardReload() {
  try {
    const nav = performance.getEntriesByType("navigation");
    return (
      (nav && nav[0] && nav[0].type === "reload") ||
      (performance.navigation && performance.navigation.type === 1)
    );
  } catch {
    return false;
  }
}

function normalizeTasksOnLoad() {
  const tasks = readTasks();
  // remove stale in-flight/interrupted tasks silently
  const normalized = tasks.filter((t) => t?.status !== "processing");
  const changed = normalized.length !== tasks.length;
  if (changed) writeTasks(normalized);
  return normalized;
}

function upsertTask(taskId, patch) {
  const tasks = readTasks();
  const idx = tasks.findIndex((t) => t.id === taskId);
  if (idx === -1) return;
  tasks[idx] = { ...tasks[idx], ...patch };
  writeTasks(tasks);
}

export function getLatestTask() {
  if (!reloadHandled && isHardReload()) {
    reloadHandled = true;
    localStorage.removeItem(STORAGE_KEY);
    return null;
  }
  reloadHandled = true;
  const tasks = normalizeTasksOnLoad();
  if (tasks.length === 0) return null;
  return tasks.sort((a, b) => (b.startedAt || 0) - (a.startedAt || 0))[0];
}

export function subscribeTaskUpdates(callback) {
  const handler = () => callback(getLatestTask());
  window.addEventListener(UPDATE_EVENT, handler);
  return () => window.removeEventListener(UPDATE_EVENT, handler);
}

export function startDocAITask({ file, action, targetLanguage }) {
  const taskId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const task = {
    id: taskId,
    status: "processing",
    action,
    targetLanguage: action === "translate" ? targetLanguage : null,
    fileName: file?.name || "Unknown.pdf",
    result: "",
    error: "",
    startedAt: Date.now(),
    completedAt: null,
  };

  const tasks = readTasks();
  tasks.push(task);
  writeTasks(tasks);

  (async () => {
    try {
      const data =
        action === "translate"
          ? await translateFile(file, targetLanguage)
          : await processFile(file, action);
      upsertTask(taskId, {
        status: "completed",
        result: data?.result || "No result returned.",
        completedAt: Date.now(),
      });
    } catch (err) {
      upsertTask(taskId, {
        status: "failed",
        error: err?.message || "An error occurred while processing.",
        completedAt: Date.now(),
      });
    }
  })();

  return taskId;
}

