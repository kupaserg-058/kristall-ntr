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

  useEffect(() => { refresh(); }, [refresh]);

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
      <div className="page-header">
        <h1 className="page-title">
          Анализ документов<br />
          <span className="page-title-accent">научно-технологического развития.</span>
        </h1>
        <p className="page-subtitle">Загрузите PDF или DOCX — система найдёт направления НТР по Указу №529</p>
      </div>

      <div className="card upload-section">
        <div
          className={`dropzone ${dragOver ? "dragover" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
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
            <>
              <div className="dz-icon">📄</div>
              <div className="dz-file">{selectedFile.name}</div>
              <div className="dz-hint">Нажмите, чтобы выбрать другой файл</div>
            </>
          ) : (
            <>
              <div className="dz-icon">↑</div>
              <div className="dz-title">Перетащите файл или нажмите для выбора</div>
              <div className="dz-hint">PDF или DOCX · до 50 МБ</div>
            </>
          )}
        </div>

        <div className="upload-controls">
          <div className="radio-group">
            <label className={`radio-option ${docType === "federal" ? "selected" : ""}`}>
              <input type="radio" name="doctype" checked={docType === "federal"} onChange={() => setDocType("federal")} />
              Федеральный
            </label>
            <label className={`radio-option ${docType === "regional" ? "selected" : ""}`}>
              <input type="radio" name="doctype" checked={docType === "regional"} onChange={() => setDocType("regional")} />
              Региональный
            </label>
          </div>

          <button className="btn btn-primary" disabled={!selectedFile || uploading} onClick={onUpload}>
            {uploading ? (
              <><span className="spinner" /> Загрузка…</>
            ) : (
              "Загрузить и анализировать"
            )}
          </button>
        </div>

        {error && <div className="form-error">{error}</div>}
      </div>

      <div className="doc-grid">
        {documents.length === 0 ? (
          <div className="doc-empty">
            <div className="doc-empty-icon">📂</div>
            <div className="doc-empty-title">Документов пока нет</div>
            <div className="muted">Загрузите первый документ выше</div>
          </div>
        ) : (
          documents.map((doc) => (
            <DocumentCard key={doc.id} doc={doc} onUpdate={updateDoc} />
          ))
        )}
      </div>
    </div>
  );
}
