/**
 * API base URLs — configure via .env (no hardcoded machine paths).
 * Create React App: variables must start with REACT_APP_
 */
const trim = (url) => (url || "").replace(/\/$/, "");

export const DOC_AI_URL = trim(
  process.env.REACT_APP_DOC_AI_URL || "http://localhost:8000"
);
export const BACKEND_URL = trim(
  process.env.REACT_APP_BACKEND_URL || "http://localhost:5001"
);

export const API = {
  docAI: `${DOC_AI_URL}/api`,
  docAIProcess: `${DOC_AI_URL}/api/process`,
  docAITranslate: `${DOC_AI_URL}/api/translate`,
  docAIQa: `${DOC_AI_URL}/api/qa_summary`,
  docAIDraft: `${DOC_AI_URL}/draft`,
  chat: `${DOC_AI_URL}/api/chat`,
  auth: {
    login: `${BACKEND_URL}/api/auth/login`,
    register: `${BACKEND_URL}/api/auth/register`,
  },
  diary: `${BACKEND_URL}/api/diary`,
};
