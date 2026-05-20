import React, { useEffect, useMemo, useState } from "react";

import CanvasPreview from "./components/CanvasPreview.jsx";
import VersionHistory from "./components/VersionHistory.jsx";

const rawApiBase = import.meta.env.VITE_API_GATEWAY_URL || "/api";
const API_BASE = rawApiBase.replace(/\/$/, "");

const DEFAULT_FORM = {
  file_name: "homepage_v2.psd",
  file_format: "psd",
  size_bytes: 560000,
  author_id: "designer_1",
  change_note: "Updated hero section and CTA",
};

function App() {
  const [serviceHealth, setServiceHealth] = useState({});
  const [projectId, setProjectId] = useState("PRJ-DEMO");
  const [versions, setVersions] = useState([]);
  const [selectedVersionId, setSelectedVersionId] = useState("VER-DEMO-1");
  const [preview, setPreview] = useState(null);
  const [form, setForm] = useState(DEFAULT_FORM);
  const [compareTarget, setCompareTarget] = useState("");
  const [diffResult, setDiffResult] = useState(null);
  const [statusLine, setStatusLine] = useState("Ready");

  const activeVersion = useMemo(
    () => versions.find((version) => version.version_id === selectedVersionId) || null,
    [versions, selectedVersionId],
  );

  async function loadHealth() {
    const response = await fetch(`${API_BASE}/services/health`);
    const payload = await response.json();
    setServiceHealth(payload);
  }

  async function loadVersions() {
    const response = await fetch(`${API_BASE}/projects/${projectId}/versions`);
    if (!response.ok) {
      setStatusLine("Cannot load version history");
      return;
    }
    const payload = await response.json();
    setVersions(payload.items || []);
    if ((payload.items || []).length && !selectedVersionId) {
      setSelectedVersionId(payload.items[0].version_id);
    }
  }

  async function loadPreview(versionId) {
    if (!versionId) return;
    const response = await fetch(`${API_BASE}/versions/${versionId}/preview`);
    if (!response.ok) {
      setPreview(null);
      return;
    }
    const payload = await response.json();
    setPreview(payload);
  }

  useEffect(() => {
    loadHealth().catch(() => setStatusLine("Gateway is not available"));
    loadVersions().catch(() => setStatusLine("Cannot connect to gateway"));
  }, []);

  useEffect(() => {
    loadPreview(selectedVersionId).catch(() => setPreview(null));
  }, [selectedVersionId]);

  async function handleUpload(event) {
    event.preventDefault();
    setStatusLine("Uploading version...");

    const response = await fetch(`${API_BASE}/workflow/upload-version?wait_for_preview=true`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: projectId,
        folder_id: "FOLDER-LAYOUTS",
        file_name: form.file_name,
        file_format: form.file_format,
        size_bytes: Number(form.size_bytes),
        author_id: form.author_id,
        change_note: form.change_note,
      }),
    });

    if (!response.ok) {
      setStatusLine("Upload failed");
      return;
    }

    const payload = await response.json();
    setStatusLine(`Uploaded ${payload.version.version_id}`);
    setSelectedVersionId(payload.version.version_id);
    setPreview(payload.preview);
    await loadVersions();
  }

  async function handleCompare(event) {
    event.preventDefault();
    if (!selectedVersionId || !compareTarget) return;

    const response = await fetch(`${API_BASE}/versions/${selectedVersionId}/compare`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        against_version_id: compareTarget,
        mode: "image",
      }),
    });

    if (!response.ok) {
      setStatusLine("Compare failed");
      return;
    }

    const payload = await response.json();
    setDiffResult(payload);
    setStatusLine("Diff calculated");
  }

  return (
    <div className="page-shell">
      <header className="top-panel">
        <div>
          <p className="eyebrow">Task 22</p>
          <h1>DesignVCS</h1>
          <p className="muted">Version control for PSD, AI, Sketch, Figma, image and video assets.</p>
        </div>
        <div className="status-badge">{statusLine}</div>
      </header>

      <section className="grid-layout">
        <article className="card upload-card">
          <h2>Upload Workflow</h2>
          <form onSubmit={handleUpload}>
            <label>
              Project ID
              <input value={projectId} onChange={(event) => setProjectId(event.target.value)} />
            </label>
            <label>
              File name
              <input
                value={form.file_name}
                onChange={(event) => setForm((prev) => ({ ...prev, file_name: event.target.value }))}
              />
            </label>
            <label>
              Format
              <select
                value={form.file_format}
                onChange={(event) => setForm((prev) => ({ ...prev, file_format: event.target.value }))}
              >
                <option value="psd">PSD</option>
                <option value="ai">AI</option>
                <option value="sketch">Sketch</option>
                <option value="figma">Figma</option>
                <option value="jpg">JPG</option>
                <option value="png">PNG</option>
                <option value="mp4">MP4</option>
                <option value="mov">MOV</option>
              </select>
            </label>
            <label>
              Size bytes
              <input
                type="number"
                min="1"
                value={form.size_bytes}
                onChange={(event) => setForm((prev) => ({ ...prev, size_bytes: event.target.value }))}
              />
            </label>
            <label>
              Author
              <input
                value={form.author_id}
                onChange={(event) => setForm((prev) => ({ ...prev, author_id: event.target.value }))}
              />
            </label>
            <label>
              Change note
              <textarea
                value={form.change_note}
                onChange={(event) => setForm((prev) => ({ ...prev, change_note: event.target.value }))}
              />
            </label>
            <button type="submit">Upload version</button>
          </form>
        </article>

        <article className="card history-card">
          <h2>Version History</h2>
          <VersionHistory
            versions={versions}
            selectedVersionId={selectedVersionId}
            onSelect={setSelectedVersionId}
          />
        </article>

        <article className="card viewer-card">
          <h2>Browser Viewer (Canvas)</h2>
          <CanvasPreview preview={preview} versionId={selectedVersionId} />
          <p className="muted">{activeVersion ? `${activeVersion.file_name} · ${activeVersion.file_format}` : "Select version"}</p>
        </article>

        <article className="card diff-card">
          <h2>Version Diff</h2>
          <form onSubmit={handleCompare} className="compare-form">
            <label>
              Compare with version ID
              <input value={compareTarget} onChange={(event) => setCompareTarget(event.target.value)} />
            </label>
            <button type="submit">Run compare</button>
          </form>
          {diffResult ? (
            <div className="diff-metrics">
              <p>Pixel delta: {diffResult.pixel_delta_pct}%</p>
              <p>Similarity: {diffResult.similarity_score}%</p>
              <p>Changed frames: {diffResult.changed_frames}</p>
              <p>{diffResult.summary}</p>
            </div>
          ) : (
            <p className="muted">Select versions and run compare.</p>
          )}
        </article>
      </section>

      <section className="card health-card">
        <h2>Service Health</h2>
        <div className="health-grid">
          {Object.entries(serviceHealth).map(([serviceName, payload]) => {
            const status =
              payload && typeof payload === "object" ? payload.status ?? "unknown" : String(payload ?? "unknown");
            return (
              <div key={serviceName} className="health-pill">
                <strong>{serviceName}</strong>
                <span>{status}</span>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

export default App;

