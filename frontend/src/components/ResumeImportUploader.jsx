import React, { useEffect, useMemo, useRef, useState } from "react";
import api from "../api/axios";
import ResumeImportLoader from "./ResumeImportLoader";
import "./ResumeImport.css";

const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".jpg", ".jpeg", ".png"];
const STAGES = [
  "Uploading resume...",
  "Extracting text...",
  "Detecting experience...",
  "Identifying skills...",
  "Preparing editable resume...",
];

const isAllowedFile = (file) => {
  const name = String(file?.name || "").toLowerCase();
  return ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext));
};

function ResumeImportUploader({ onStartScratch, onImportSuccess }) {
  const [mode, setMode] = useState("scratch");
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [stageIndex, setStageIndex] = useState(0);
  const [lastFileName, setLastFileName] = useState("");
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (!loading) return undefined;
    const timer = setInterval(() => {
      setStageIndex((prev) => Math.min(prev + 1, STAGES.length - 1));
    }, 1300);
    return () => clearInterval(timer);
  }, [loading]);

  const stageText = useMemo(() => STAGES[stageIndex] || STAGES[0], [stageIndex]);

  const resetError = () => setError("");

  const handleFile = (pickedFile) => {
    resetError();
    if (!pickedFile) return;
    if (!isAllowedFile(pickedFile)) {
      setError("Unsupported format. Use pdf, docx, jpg, jpeg, or png.");
      return;
    }
    setFile(pickedFile);
    setLastFileName(pickedFile.name || "");
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setDragOver(false);
    const droppedFile = event.dataTransfer?.files?.[0];
    handleFile(droppedFile);
  };

  const handleSubmit = async () => {
    resetError();
    if (mode === "scratch") {
      onStartScratch?.();
      return;
    }

    if (!file) {
      setError("Choose a resume file to import.");
      return;
    }

    setLoading(true);
    setProgress(0);
    setStageIndex(0);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await api.post("/resumes/import", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 120000,
        onUploadProgress: (evt) => {
          if (!evt?.total) return;
          const pct = Math.round((evt.loaded / evt.total) * 100);
          setProgress(Math.min(95, Math.max(5, pct)));
          if (pct > 40) setStageIndex((prev) => Math.max(prev, 1));
          if (pct > 70) setStageIndex((prev) => Math.max(prev, 2));
        },
      });

      setProgress(100);
      setStageIndex(STAGES.length - 1);
      onImportSuccess?.(response.data);
    } catch (err) {
      const code = err?.response?.data?.code;
      const message = err?.response?.data?.error || "Import failed. Please try again.";
      const parserDetail =
        err?.response?.data?.details?.message ||
        err?.response?.data?.details?.error ||
        "";
      if (code === "parser_unavailable") {
        setError("Parser service is unavailable right now. Please retry in a moment.");
      } else if (code === "invalid_parser_response") {
        setError("Parser returned invalid structured data. Please retry or use another file.");
      } else if (code === "unsupported_format") {
        setError("Unsupported format. Use pdf, docx, jpg, jpeg, or png.");
      } else if (code === "file_too_large") {
        setError("File too large. Please upload a file under 10MB.");
      } else if (code === "parser_request_error") {
        setError(
          parserDetail
            ? `Parser could not process this resume: ${parserDetail}`
            : "Parser could not process this resume. Please retry with a clearer file."
        );
      } else if (code === "parser_server_error" || code === "parser_unavailable") {
        setError("Parser timeout/unavailable. Please retry.");
      } else {
        setError(message);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="import-flow-shell">
      <div className="import-flow-card">
        <h2>Create Resume</h2>
        <p>Choose how you want to begin.</p>

        <div className="import-mode-group">
          <label className={`import-mode ${mode === "scratch" ? "active" : ""}`}>
            <input
              type="radio"
              name="create-mode"
              checked={mode === "scratch"}
              onChange={() => setMode("scratch")}
            />
            Start From Scratch
          </label>

          <label className={`import-mode ${mode === "upload" ? "active" : ""}`}>
            <input
              type="radio"
              name="create-mode"
              checked={mode === "upload"}
              onChange={() => setMode("upload")}
            />
            Upload Existing Resume
          </label>
        </div>

        {mode === "upload" && (
          <div className="import-upload-area">
            <div
              className={`import-dropzone ${dragOver ? "drag-over" : ""}`}
              onDragOver={(event) => {
                event.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
            >
              <p>Drag & drop your resume here</p>
              <span>or</span>
              <button
                type="button"
                className="import-browse-btn"
                onClick={() => fileInputRef.current?.click()}
              >
                Browse File
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept={ALLOWED_EXTENSIONS.join(",")}
                style={{ display: "none" }}
                onChange={(event) => handleFile(event.target.files?.[0])}
              />
            </div>
            <small>Supported: PDF, DOCX, JPG, JPEG, PNG</small>
            {file ? <div className="import-file-pill">{file.name}</div> : null}
            {!file && lastFileName ? <div className="import-file-pill">{lastFileName}</div> : null}
          </div>
        )}

        {loading ? <ResumeImportLoader stage={stageText} progress={progress} /> : null}

        {error ? (
          <div className="import-error-box">
            <span>{error}</span>
            <button type="button" onClick={handleSubmit}>
              Retry
            </button>
          </div>
        ) : null}

        <div className="import-actions">
          <button type="button" className="import-continue-btn" onClick={handleSubmit} disabled={loading}>
            {mode === "scratch" ? "Continue" : "Import Resume"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ResumeImportUploader;
