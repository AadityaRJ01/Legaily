const STORAGE_KEY = "judgeUploadState";
const UPDATE_EVENT = "judge-upload-updated";

let activeUpload = null;

function readState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    if (!parsed) return { status: "idle", cid: "", error: "", fileName: "" };
    return {
      status: parsed.status || "idle",
      cid: parsed.cid || "",
      error: parsed.error || "",
      fileName: parsed.fileName || "",
    };
  } catch {
    return { status: "idle", cid: "", error: "", fileName: "" };
  }
}

function writeState(next) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  window.dispatchEvent(new CustomEvent(UPDATE_EVENT));
}

function normalizeOnLoad() {
  const state = readState();
  // A hard refresh kills the in-flight request; avoid stuck "uploading" forever.
  if (state.status === "uploading" && !activeUpload) {
    writeState({
      ...state,
      status: "idle",
      error: "",
    });
    return readState();
  }
  return state;
}

export function getJudgeUploadState() {
  return normalizeOnLoad();
}

export function subscribeJudgeUpload(callback) {
  const handler = () => callback(readState());
  window.addEventListener(UPDATE_EVENT, handler);
  return () => window.removeEventListener(UPDATE_EVENT, handler);
}

export function startJudgeUpload({ file, useJWT, pinataJWT, pinataApiKey, pinataApiSecret }) {
  if (!file) throw new Error("Please select a file");
  const current = readState();
  if (current.status === "uploading") return;

  writeState({ status: "uploading", cid: current.cid || "", error: "", fileName: file.name || "" });

  activeUpload = (async () => {
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("pinataOptions", JSON.stringify({ cidVersion: 1 }));

      const response = await fetch("https://api.pinata.cloud/pinning/pinFileToIPFS", {
        method: "POST",
        headers: useJWT
          ? { Authorization: `Bearer ${pinataJWT}` }
          : {
              pinata_api_key: pinataApiKey,
              pinata_secret_api_key: pinataApiSecret,
            },
        body: formData,
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      writeState({ status: "completed", cid: data.IpfsHash || "", error: "", fileName: file.name || "" });
    } catch (err) {
      writeState({
        status: "failed",
        cid: readState().cid || "",
        error: err?.message || "Upload failed",
        fileName: file.name || "",
      });
    } finally {
      activeUpload = null;
    }
  })();
}

