import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import DirectionRow from "../components/DirectionRow.jsx";
import { FEDERAL_DIRECTIONS, getStats, listDirections, updateDirectionStatus } from "../api.js";

const VERIFICATION_OPTIONS = [
  { value: "", label: "Все статусы" },
  { value: "pending", label: "Ожидает" },
  { value: "confirmed", label: "Подтверждено" },
  { value: "needs_clarification", label: "Требует уточнения" },
  { value: "rejected", label: "Отклонено" },
];

export default function DirectionsPage() {
  const [searchParams] = useSearchParams();
  const docId = searchParams.get("doc_id") || "";

  const [directions, setDirections] = useState([]);
  const [stats, setStats] = useState(null);
  const [federal, setFederal] = useState("");
  const [verification, setVerification] = useState("");
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setError("");
    try {
      const [dirs, st] = await Promise.all([
        listDirections({
          doc_id: docId || undefined,
          federal_match: federal || undefined,
          verification_status: verification || undefined,
        }),
        getStats(),
      ]);
      setDirections(dirs);
      setStats(st);
    } catch (e) {
      setError(e.message);
    }
  }, [docId, federal, verification]);

  useEffect(() => { refresh(); }, [refresh]);

  const onChangeStatus = async (id, status) => {
    try {
      await updateDirectionStatus(id, status);
      await refresh();
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Направления НТР</h1>
        <p className="page-subtitle">Результаты анализа документов по Указу №529</p>
      </div>

      {stats && (
        <div className="stats-grid">
          <div className="stat">
            <span className="stat-num stat-blue">{stats.total_directions}</span>
            <div className="stat-label">Всего направлений</div>
          </div>
          <div className="stat">
            <span className="stat-num stat-green">{stats.confirmed}</span>
            <div className="stat-label">Подтверждено</div>
          </div>
          <div className="stat">
            <span className="stat-num stat-grey">{stats.pending}</span>
            <div className="stat-label">Ожидает</div>
          </div>
          <div className="stat">
            <span className="stat-num">{stats.total_documents}</span>
            <div className="stat-label">Документов</div>
          </div>
        </div>
      )}

      <div className="filters-row">
        <select
          className="filter-select"
          value={federal}
          onChange={(e) => setFederal(e.target.value)}
        >
          <option value="">Все федеральные направления</option>
          {FEDERAL_DIRECTIONS.map((f) => (
            <option key={f} value={f}>{f}</option>
          ))}
        </select>
        <select
          className="filter-select"
          value={verification}
          onChange={(e) => setVerification(e.target.value)}
        >
          {VERIFICATION_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        {docId && <span className="filter-note">Фильтр по документу активен</span>}
      </div>

      {error && <div className="form-error">{error}</div>}

      <div className="table-wrap">
        <table className="dir-table">
          <thead>
            <tr>
              <th>Направление</th>
              <th>Фед. направление</th>
              <th>Документ</th>
              <th>Фрагмент</th>
              <th>Уверенность</th>
              <th>Статус</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            {directions.length === 0 ? (
              <tr className="empty-table">
                <td colSpan={7}>
                  <div className="empty-table-icon">🔍</div>
                  <div className="empty-table-text">Направлений не найдено</div>
                </td>
              </tr>
            ) : (
              directions.map((d) => (
                <DirectionRow key={d.id} direction={d} onChangeStatus={onChangeStatus} />
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
