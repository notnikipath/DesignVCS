import React from "react";

function VersionHistory({ versions, selectedVersionId, onSelect }) {
  if (!versions.length) {
    return <p className="muted">No versions yet</p>;
  }

  return (
    <div className="history-list">
      {versions.map((version) => {
        const isActive = selectedVersionId === version.version_id;
        return (
          <button
            key={version.version_id}
            type="button"
            className={`history-item ${isActive ? "active" : ""}`}
            onClick={() => onSelect(version.version_id)}
          >
            <strong>v{version.sequence_number}</strong>
            <span>{version.file_name}</span>
            <small>
              {version.file_format.toUpperCase()} · {Math.round(version.size_bytes / 1024)} KB
            </small>
          </button>
        );
      })}
    </div>
  );
}

export default VersionHistory;
