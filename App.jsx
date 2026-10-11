import React, { useState } from 'react';
import { summarizeDocument } from './services/api';

export default function App() {
  const [inputText, setInputText] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSummarize = async () => {
    if (!inputText.trim()) {
      alert("Please enter some text first.");
      return;
    }
    setLoading(true);
    try {
      const data = await summarizeDocument(inputText, "Hindi");
      setResult(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <textarea 
        value={inputText} 
        onChange={(e) => setInputText(e.target.value)} 
        placeholder="Paste legal order here..."
      />
      <button onClick={handleSummarize} disabled={loading}>
        {loading ? "Analyzing..." : "Explain Simply"}
      </button>

      {result && (
        <div>
          <h3>{result.case_headline}</h3>
          <p><strong>Status:</strong> {result.verdict_summary}</p>
          <p><strong>Jail Risk:</strong> {result.the_big_three?.jail_or_arrest_risk}</p>
        </div>
      )}
    </div>
  );
}
