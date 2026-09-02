const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
  "http://127.0.0.1:8000";

export const DEMO_USER_ID =
  process.env.NEXT_PUBLIC_USER_ID ||
  "00000000-0000-0000-0000-000000000001";

function headers(extra = {}) {
  return {
    "Content-Type": "application/json",
    "X-Platform-User-Id": DEMO_USER_ID,
    "X-User-Id": DEMO_USER_ID,
    ...extra,
  };
}

async function parseError(res) {
  let detail = res.statusText;
  try {
    const body = await res.json();
    detail = body.detail || JSON.stringify(body);
  } catch {
    /* ignore */
  }
  const err = new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  err.status = res.status;
  throw err;
}

export async function fetchBalance() {
  const res = await fetch(`${API_URL}/wallet/balance`, {
    headers: headers(),
    cache: "no-store",
  });
  if (!res.ok) await parseError(res);
  return res.json();
}

export async function fetchTasks() {
  const res = await fetch(`${API_URL}/tasks`, {
    headers: headers(),
    cache: "no-store",
  });
  if (!res.ok) await parseError(res);
  return res.json();
}

export async function createTask(payload) {
  const res = await fetch(`${API_URL}/tasks`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) await parseError(res);
  return res.json();
}

export async function respondTask(taskId) {
  const res = await fetch(`${API_URL}/tasks/${taskId}/respond`, {
    method: "POST",
    headers: headers(),
  });
  if (!res.ok) await parseError(res);
  return res.json();
}

export async function buyCredits(amount) {
  const res = await fetch(`${API_URL}/wallet/topup`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ amount }),
  });
  if (!res.ok) await parseError(res);
  return res.json();
}

export async function executePrompt(prompt, model = "deepseek-chat") {
  const res = await fetch(`${API_URL}/v1/chat/completions`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({
      model,
      messages: [{ role: "user", content: prompt }],
      stream: false,
    }),
  });
  if (!res.ok) await parseError(res);
  const data = await res.json();
  const deducted = Number(res.headers.get("X-Credits-Deducted") || 0);
  const remaining = Number(res.headers.get("X-Credits-Remaining") || NaN);
  const usage = data.usage || {};
  const tokens =
    Number(usage.total_tokens || 0) ||
    Number(usage.prompt_tokens || 0) + Number(usage.completion_tokens || 0);
  const content =
    data.choices?.[0]?.message?.content ||
    data.choices?.[0]?.text ||
    "(empty response)";
  return { content, tokens, deducted, remaining, raw: data };
}

export function formatCredits(n) {
  return new Intl.NumberFormat("fr-FR").format(Number(n || 0));
}
