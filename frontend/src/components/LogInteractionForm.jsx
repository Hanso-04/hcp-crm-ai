import React from "react";
import { useSelector, useDispatch } from "react-redux";
import { confirmInteraction } from "../store/interactionSlice";
import "./LogInteractionForm.css";

const INTERACTION_TYPES = ["Meeting", "Call", "Email", "Conference"];

function LockedField({ label, changed, children }) {
  return (
    <div className={`field ${changed ? "field-changed" : ""}`}>
      <div className="field-label-row">
        <label>{label}</label>
        <span className="lock-badge" title="Only the AI assistant can fill this field">
          🔒 AI-filled
        </span>
      </div>
      {children}
    </div>
  );
}

export default function LogInteractionForm() {
  const dispatch = useDispatch();
  const { draft, changedFields, hcpHistory, saveStatus } = useSelector((s) => s.interaction);

  const isChanged = (key) => changedFields.includes(key);
  const canSave = Boolean(draft.hcp_name);

  return (
    <div className="log-form">
      <div className="log-form-scroll">
        <h2>Interaction Details</h2>

        {draft.compliance_flag && (
          <div className="compliance-banner">
            <strong>⚠ Compliance review flagged</strong>
            <p>{draft.compliance_notes || "This interaction needs a compliance review."}</p>
          </div>
        )}

        <div className="field-grid">
          <LockedField label="HCP Name" changed={isChanged("hcp_name")}>
            <input type="text" readOnly value={draft.hcp_name || ""} placeholder="Filled by AI assistant…" />
          </LockedField>

          <LockedField label="Interaction Type" changed={isChanged("interaction_type")}>
            <select disabled value={draft.interaction_type || "Meeting"}>
              {INTERACTION_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </LockedField>

          <LockedField label="Date" changed={isChanged("interaction_date")}>
            <input type="text" readOnly value={draft.interaction_date || ""} placeholder="YYYY-MM-DD" />
          </LockedField>

          <LockedField label="Time" changed={isChanged("interaction_time")}>
            <input type="text" readOnly value={draft.interaction_time || ""} placeholder="HH:MM AM/PM" />
          </LockedField>
        </div>

        <LockedField label="Attendees" changed={isChanged("attendees")}>
          <input type="text" readOnly value={draft.attendees || ""} placeholder="Filled by AI assistant…" />
        </LockedField>

        <LockedField label="Topics Discussed" changed={isChanged("topics_discussed")}>
          <textarea readOnly rows={3} value={draft.topics_discussed || ""} placeholder="Filled by AI assistant…" />
        </LockedField>

        <LockedField label="Materials Shared" changed={isChanged("materials_shared")}>
          <textarea readOnly rows={2} value={draft.materials_shared || ""} placeholder="Filled by AI assistant…" />
        </LockedField>

        <div className="field-grid">
          <div className="field">
            <div className="field-label-row">
              <label>Sentiment</label>
            </div>
            {draft.sentiment ? (
              <span className={`sentiment-pill sentiment-${draft.sentiment}`}>{draft.sentiment}</span>
            ) : (
              <span className="sentiment-pill sentiment-empty">Not assessed yet</span>
            )}
          </div>
        </div>

        {hcpHistory && hcpHistory.length > 0 && (
          <div className="history-panel">
            <h3>Prior interactions with this HCP</h3>
            <ul>
              {hcpHistory.map((h, i) => (
                <li key={i}>
                  <span className="history-date">{h.date || "Undated"}</span> — {h.type}: {h.topics || "—"}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="log-form-footer">
        <button
          className="btn-primary"
          disabled={!canSave || saveStatus === "saving"}
          onClick={() => dispatch(confirmInteraction())}
        >
          {saveStatus === "saving" ? "Saving…" : "Confirm & Save"}
        </button>
        {saveStatus === "saved" && <span className="save-status save-status-ok">Saved ✓</span>}
        {saveStatus === "error" && <span className="save-status save-status-error">Save failed — retry</span>}
      </div>
    </div>
  );
}
