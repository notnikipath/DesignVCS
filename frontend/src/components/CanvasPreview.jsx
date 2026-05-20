import React, { useEffect, useRef } from "react";

function CanvasPreview({ preview, versionId }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
    gradient.addColorStop(0, "#0e1e40");
    gradient.addColorStop(1, "#1f5b7d");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.fillStyle = "rgba(255, 255, 255, 0.12)";
    for (let index = 0; index < 9; index += 1) {
      ctx.fillRect(index * 70, (index % 3) * 60 + 20, 120, 36);
    }

    ctx.fillStyle = "#f8f5ec";
    ctx.font = "600 18px 'Space Grotesk', sans-serif";
    ctx.fillText("Design Preview", 22, 34);

    ctx.font = "500 13px 'IBM Plex Mono', monospace";
    ctx.fillText(`Version: ${versionId || "-"}`, 22, 62);

    if (preview?.preview_key) {
      ctx.fillText(`Key: ${preview.preview_key}`, 22, 86);
      ctx.fillText(`Generation: ${preview.generation_ms ?? 0} ms`, 22, 108);
    } else {
      ctx.fillText("Preview is not generated yet", 22, 86);
    }

    ctx.strokeStyle = "#ffcf70";
    ctx.lineWidth = 2;
    ctx.strokeRect(18, 16, canvas.width - 36, canvas.height - 32);
  }, [preview, versionId]);

  return <canvas ref={canvasRef} className="preview-canvas" width={620} height={300} />;
}

export default CanvasPreview;

