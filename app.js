// src/services/api.js

export async function summarizeDocument(text, language = "Hindi") {
  const formData = new FormData();
  formData.append("text", text);
  formData.append("language", language);

  const response = await fetch("http://localhost:8000/api/summarize", {
    method: "POST",
    body: formData
  });

  if (!response.ok) {
    throw new Error(`Server error: ${response.status}`);
  }

  const data = await response.json();
  return data;
}
