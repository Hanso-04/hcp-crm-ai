import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { sendAgentMessage } from "../api/agentApi";
import { applyAgentUpdate } from "./interactionSlice";

export const sendMessage = createAsyncThunk(
  "chat/sendMessage",
  async (userText, { getState, dispatch }) => {
    const { interaction, chat } = getState();

    dispatch(chatSlice.actions.addMessage({ role: "user", content: userText }));

    const result = await sendAgentMessage({
      message: userText,
      currentDraft: interaction.draft,
      interactionId: interaction.interactionId,
      voiceNoteConsent: chat.voiceNoteConsent,
    });

    dispatch(
      applyAgentUpdate({
        draft: result.draft,
        changedFields: result.changed_fields,
        hcpHistory: result.hcp_history,
      })
    );

    return result;
  }
);

const chatSlice = createSlice({
  name: "chat",
  initialState: {
    messages: [
      {
        role: "assistant",
        content:
          "Log interaction details here (e.g. \"Met Dr. Mehta, discussed Prodo-X efficacy, positive sentiment, shared brochure\") or ask for help.",
      },
    ],
    voiceNoteConsent: false,
    loading: false,
  },
  reducers: {
    addMessage(state, action) {
      state.messages.push(action.payload);
    },
    toggleVoiceNoteConsent(state) {
      state.voiceNoteConsent = !state.voiceNoteConsent;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state) => {
        state.loading = true;
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.loading = false;
        state.messages.push({ role: "assistant", content: action.payload.reply, toolCalls: action.payload.tool_calls });
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.loading = false;
        state.messages.push({
          role: "assistant",
          content: "Something went wrong reaching the assistant. Please try again.",
          error: true,
        });
        console.error(action.error);
      });
  },
});

export const { toggleVoiceNoteConsent } = chatSlice.actions;
export default chatSlice.reducer;
