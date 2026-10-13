import { AppFrame } from "./AppFrame";
import React from "react";
import { createRoot } from "react-dom/client";

import App from "./App.jsx";
import "./styles.css";

class RootErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, message: "" };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, message: String(error?.message || error || "Unknown runtime error") };
  }

  componentDidCatch(error) {
    // Keep trace in console for local debugging.
    // eslint-disable-next-line no-console
    console.error("DesignVCS frontend crash:", error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <main
          style={{
            minHeight: "100vh",
            display: "grid",
            placeItems: "center",
            background: "#0f1724",
            color: "#f7f5ea",
            padding: "24px",
            fontFamily: "monospace",
          }}
        >
          <div>
            <h2 style={{ marginTop: 0 }}>Frontend Runtime Error</h2>
            <p style={{ marginBottom: 0 }}>{this.state.message}</p>
          </div>
        </main>
      );
    }
    return this.props.children;
  }
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <RootErrorBoundary>
      <AppFrame><App /></AppFrame>
    </RootErrorBoundary>
  </React.StrictMode>,
);
