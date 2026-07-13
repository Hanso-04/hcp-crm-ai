import axios from "axios";

const BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

const client = axios.create({ baseURL: BASE_URL });

/** Send a chat message to the LangGraph agent. The current draft is sent
 * along so multi-turn edits (Edit Interaction tool) know what already exists. */
export const sendAgentMessage = async ({
  message,
  currentDraft,
  interactionId,
  voiceNoteConsent,
}) => {
  const { data } = await client.post("/agent/chat", {
    message,
    current_draft: currentDraft,
    interaction_id: interactionId,
    voice_note_consent: voiceNoteConsent,
  });
  return data;
};

/** Persist a reviewed/confirmed draft. This is the only call that writes to
 * the database — it fires when the rep clicks "Confirm & Save", never on
 * every keystroke, since there are no keystrokes: only the agent writes. */
export const confirmInteractionApi = async ({ draft, interactionId }) => {
  const { data } = await client.post("/interactions", {
    draft,
    interaction_id: interactionId,
  });
  return data;
};

export const fetchInteractions = async () => {
  const { data } = await client.get("/interactions");
  return data;
};

export default client;
