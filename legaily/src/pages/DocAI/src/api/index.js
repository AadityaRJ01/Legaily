import axios from "axios";
import { API } from "../../../../config/api";

const BASE_URL = API.docAI;

export const processFile = async (file, action) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("action", action);

  const response = await axios.post(`${BASE_URL}/process/`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

  return response.data;
};

export const translateFile = async (file, targetLanguage) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("target_language", targetLanguage);

  const response = await axios.post(`${BASE_URL}/translate/`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

  return response.data;
};

export const askSummaryQuestion = async ({
  question,
  fullText = "",
  summaryText = "",
  history = [],
}) => {
  const response = await axios.post(`${BASE_URL}/qa_summary/`, {
    question,
    full_text: fullText,
    summary_text: summaryText,
    history,
  });

  return response.data;
};
