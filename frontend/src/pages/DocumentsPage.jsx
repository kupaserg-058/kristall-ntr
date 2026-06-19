import { useCallback, useEffect, useRef, useState } from "react";
import DocumentCard from "../components/DocumentCard.jsx";
import { analyzeDocument, listDocuments, uploadDocument } from "../api.js";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState([]);
  const [docType, setDocType] = useState("federal");
  const [selectedFile, setSelectedFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const fileInputRef = useRef(null);

  const refresh = useCallback(async () => {
    try {
      const docs = await listDocuments();
      setDocuments(docs);
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const validate = (file) => {
    const name = file.name.toLowerCase();
    return name.endsWith(".pdf") || name.endsWith(".docx");
  };

  const pickFile = (file) => {
    if (!file) return;
    if (!validate(file)) {
      setError("Поддерживаются только файлы .pdf и .docx");
      return;
    }
    setError("");
    setSelectedFile(file);
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    pickFile(e.dataTransfer.files?.[0]);
  };

  const onUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setError("");
    try {
      const doc = await uploadDocument(selectedFile, docType);
      await analyzeDocument(doc.id);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      await refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  };

  const updateDoc = useCallback((fresh) => {
    setDocuments((prev) => prev.map((d) => (d.id === fresh.id ? fresh : d)));
  }, []);

  return (
    <div className="page">
      <h1 className="page-title">Документы</h1>

      <div className="card upload-card">
        <div
          className={`dropzone ${dragOver ? "dragover" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx"
            hidden
            onChange={(e) => pickFile(e.target.files?.[0])}
          />
          {selectedFile ? (
            <span className="dz-file">{selectedFile.name}</span>
          ) : (
            <span className="dz-hint">
              Перетащите файл сюда или нажмите для выбора
              <br />
              <small>PDF или DOCX</small>
            </span>
          )}
        </div>

        <div className="upload-controls">
          <div className="radio-group">
            <label>
              <input
                type="radio"
                name="doctype"
                checked={docType === "federal"}
                onChange={() => setDocType("federal")}
              />
              Федеральный
            </label>
            <label>
              <input
                type="radio"
                name="doctype"
                checked={docType === "regional"}
                onChange={() => setDocType("regional")}
              />
              Региональный
            </label>
          </div>

          <button
            className="btn btn-primary"
            disabled={!selectedFile || uploading}
            onClick={onUpload}
          >
            {uploading ? "Загрузка…" : "Загрузить и анализировать"}
          </button>
        </div>

        {error && <div className="form-error">{error}</div>}
      </div>

      <div className="doc-grid">
        {documents.length === 0 && (
          <p className="muted">Документов пока нет. Загрузите первый документ.</p>
        )}
        {documents.map((doc) => (
          <DocumentCard key={doc.id} doc={doc} onUpdate={updateDoc} />
        ))}
      </div>
    </div>
  );
}
