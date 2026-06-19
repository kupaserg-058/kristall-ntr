const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function handle(res) {
  if (!res.ok) {
    let detail = `Ошибка ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch {
      // тело не JSON — оставляем дефолтное сообщение
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function uploadDocument(file, docType) {
  const form = new FormData();
  form.append("file", file);
  form.append("doc_type", docType);
  const res = await fetch(`${BASE_URL}/api/documents/upload`, {
    method: "POST",
    body: form,
  });
  return handle(res);
}

export async function analyzeDocument(id) {
  const res = await fetch(`${BASE_URL}/api/documents/${id}/analyze`, {
    method: "POST",
  });
  return handle(res);
}

export async function listDocuments() {
  const res = await fetch(`${BASE_URL}/api/documents`);
  return handle(res);
}

export async function getDocument(id) {
  const res = await fetch(`${BASE_URL}/api/documents/${id}`);
  return handle(res);
}

export async function getDocumentDirections(id) {
  const res = await fetch(`${BASE_URL}/api/documents/${id}/directions`);
  return handle(res);
}

export async function listDirections(filters = {}) {
  const params = new URLSearchParams();
  if (filters.doc_id) params.append("doc_id", filters.doc_id);
  if (filters.federal_match) params.append("federal_match", filters.federal_match);
  if (filters.verification_status)
    params.append("verification_status", filters.verification_status);
  const qs = params.toString();
  const res = await fetch(`${BASE_URL}/api/directions${qs ? `?${qs}` : ""}`);
  return handle(res);
}

export async function updateDirectionStatus(id, status) {
  const res = await fetch(`${BASE_URL}/api/directions/${id}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  return handle(res);
}

export async function getStats() {
  const res = await fetch(`${BASE_URL}/api/stats`);
  return handle(res);
}

export const FEDERAL_DIRECTIONS = [
  "Высокоэффективная и ресурсосберегающая энергетика",
  "Превентивная и персонализированная медицина, обеспечение здорового долголетия",
  "Высокопродуктивное и устойчивое к изменениям природной среды сельское хозяйство",
  "Безопасность получения, хранения, передачи и обработки информации",
  "Интеллектуальные транспортные и телекоммуникационные системы, включая автономные транспортные средства",
  "Укрепление социокультурной идентичности российского общества и повышение уровня его образования",
  "Адаптация к изменениям климата, сохранение и рациональное использование природных ресурсов",
];
