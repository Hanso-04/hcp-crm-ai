import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { confirmInteractionApi } from "../api/agentApi";

const emptyDraft = {
  hcp_name: "",
  interaction_type: "Meeting",
  interaction_date: "",
  interaction_time: "",
  attendees: "",
  topics_discussed: "",
  materials_shared: "",
  sentiment: "",
  compliance_flag: false,
  compliance_notes: "",
};

export const confirmInteraction = createAsyncThunk(
  "interaction/confirm",
  async (_, { getState }) => {
    const { interaction } = getState();
    return confirmInteractionApi({
      draft: interaction.draft,
      interactionId: interaction.interactionId,
    });
  }
);

const interactionSlice = createSlice({
  name: "interaction",
  initialState: {
    draft: emptyDraft,
    changedFields: [],
    interactionId: null,
    hcpHistory: [],
    saveStatus: "idle", // idle | saving | saved | error
  },
  reducers: {
    // The ONLY place a full draft replacement happens — driven exclusively
    // by what the agent returned, never by a form onChange handler.
    applyAgentUpdate(state, action) {
      const { draft, changedFields, hcpHistory } = action.payload;
      state.draft = { ...state.draft, ...draft };
      state.changedFields = changedFields || [];
      if (hcpHistory) state.hcpHistory = hcpHistory;
    },
    startNewInteraction(state) {
      state.draft = emptyDraft;
      state.changedFields = [];
      state.interactionId = null;
      state.hcpHistory = [];
      state.saveStatus = "idle";
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(confirmInteraction.pending, (state) => {
        state.saveStatus = "saving";
      })
      .addCase(confirmInteraction.fulfilled, (state, action) => {
        state.saveStatus = "saved";
        state.interactionId = action.payload.id;
      })
      .addCase(confirmInteraction.rejected, (state) => {
        state.saveStatus = "error";
      });
  },
});

export const { applyAgentUpdate, startNewInteraction } = interactionSlice.actions;
export default interactionSlice.reducer;
