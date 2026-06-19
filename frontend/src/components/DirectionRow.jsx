import { useState } from "react";
import StatusBadge from "./StatusBadge.jsx";

const ACTIONS = [
  { status: "confirmed", symbol: "✓", title: "Подтвердить", cls: "act-confirm" },
  {
    status: "needs_clarification",
    symbol: "?",
    title: "Требует уточнения",
    cls: "act-clarify",
  },
  { status: "rejected", symbol: "✗", title: "Отклонить", cls: "act-reject" },
];

export default function DirectionRow({ direction, onChangeStatus }) {
  const [expanded, setExpanded] = useState(false);

  const fragment = direction.fragment || "";
  const isLong = fragment.length > 80;
  const shown = expanded || !isLong ? fragment : `${fragment.slice(0, 80)}…`;

  return (
    <tr>
      <td className="cell-title">{direction.title}</td>
      <td>{direction.federal_match || <span className="muted">—</span>}</td>
      <td className="muted">{direction.document_name || "—"}</td>
      <td
        className={isLong ? "cell-fragment clickable" : "cell-fragment"}
        onClick={() => isLong && setExpanded((v) => !v)}
        title={isLong ? "Нажмите, чтобы развернуть" : ""}
      >
        {shown || <span className="muted">—</span>}
      </td>
      <td>
        <StatusBadge kind="confidence" value={direction.confidence} />
      </td>
      <td>
        <StatusBadge kind="verification" value={direction.verification_status} />
      </td>
      <td>
        <div className="actions">
          {ACTIONS.map((a) => (
            <button
              key={a.status}
              className={`act-btn ${a.cls} ${
                direction.verification_status === a.status ? "active" : ""
              }`}
              title={a.title}
              onClick={() => onChangeStatus(direction.id, a.status)}
            >
              {a.symbol}
            </button>
          ))}
        </div>
      </td>
    </tr>
  );
}
