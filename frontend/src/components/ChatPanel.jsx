import React, { useState, useRef, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import { sendMessage } from "../store/chatSlice";
import { toggleVoiceNoteConsent } from "../store/chatSlice";
import "./ChatPanel.css";

const SUGGESTIONS = [
  "Met Dr. Mehta, discussed Prodo-X efficacy, positive sentiment, shared brochure",
  "Actually it was Dr. Kapoor, not Dr. Mehta",
  "Log another visit to Dr. Mehta",
];

export default function ChatPanel() {
  const dispatch = useDispatch();
  const { messages, loading, voiceNoteConsent } = useSelector((s) => s.chat);
  const [input, setInput] = useState("");
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  const submit = () => {
    const text = input.trim();
    if (!text || loading) return;
    dispatch(sendMessage(text));
    setInput("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <span className="chat-header-icon">🤖</span>
        <div>
          <div className="chat-header-title">AI Assistant</div>
          <div className="chat-header-subtitle">Log interaction details here via chat</div>
        </div>
      </div>

      <div className="chat-messages" ref={scrollRef}>
        {messages.map((m, i) => (
          <div key={i} className={`chat-bubble chat-bubble-${m.role} ${m.error ? "chat-bubble-error" : ""}`}>
            {m.content}
            {m.toolCalls && m.toolCalls.length > 0 && (
              <div className="tool-chip-row">
                {m.toolCalls.map((t, idx) => (
                  <span className="tool-chip" key={idx}>
                    {t}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && <div className="chat-bubble chat-bubble-assistant chat-bubble-loading">Thinking…</div>}
      </div>

      {messages.length <= 1 && (
        <div className="suggestions">
          {SUGGESTIONS.map((s, i) => (
            <button key={i} className="suggestion-chip" onClick={() => setInput(s)}>
              {s}
            </button>
          ))}
        </div>
      )}

      <label className="consent-row">
        <input type="checkbox" checked={voiceNoteConsent} onChange={() => dispatch(toggleVoiceNoteConsent())} />
        Summarize from Voice Note (Requires Consent)
      </label>

      <div className="chat-input-row">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Describe interaction…"
          rows={1}
        />
        <button className="btn-send" onClick={submit} disabled={loading || !input.trim()}>
          Log
        </button>
      </div>
    </div>
  );
}
