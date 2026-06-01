import React from "react";

function ResumeImportLoader({ stage, progress }) {
  const clampedProgress = Math.max(0, Math.min(100, Number(progress) || 0));

  return (
    <div className="import-loader-card">
      <div className="import-loader-spinner" />
      <h4>{stage || "Preparing import..."}</h4>
      <div className="import-loader-bar">
        <div
          className="import-loader-fill"
          style={{ width: `${clampedProgress}%` }}
        />
      </div>
      <p>{clampedProgress}%</p>
    </div>
  );
}

export default ResumeImportLoader;
