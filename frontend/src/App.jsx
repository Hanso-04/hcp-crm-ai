import React from "react";
import { useDispatch } from "react-redux";
import LogInteractionForm from "./components/LogInteractionForm";
import ChatPanel from "./components/ChatPanel";
import { startNewInteraction } from "./store/interactionSlice";
import "./App.css";

export default function App() {
  const dispatch = useDispatch();

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1>Log HCP Interaction</h1>
          <p className="app-subtitle">AI-first interaction logging for field reps</p>
        </div>
        <button className="btn-ghost" onClick={() => dispatch(startNewInteraction())}>
          + New interaction
        </button>
      </header>

      <main className="split-screen">
        <section className="pane pane-form">
          <LogInteractionForm />
        </section>
        <section className="pane pane-chat">
          <ChatPanel />
        </section>
      </main>
    </div>
  );
}
