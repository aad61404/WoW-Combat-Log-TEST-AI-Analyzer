export type Fight = {
  id: number;
  name: string;
  start_time: number;
  end_time: number;
  kill: boolean;
  difficulty: number | null;
  fight_percentage: number | null;
};
export type Report = {
  code: string;
  title: string;
  owner: string;
  fights: Fight[];
  actors: { type: string; name: string }[];
};
export type Evidence = {
  player_id: number | null;
  timestamp: number;
  type: string;
  severity: string;
  player: string | null;
  description: string;
};
export type Death = {
  player_id: number | null;
  timestamp: number;
  player: string;
  killing_blow: string | null;
  damage_taken_last_5s: {
    timestamp: number;
    source: string;
    ability: string;
    amount: number;
  }[];
};
export type Analysis = {
  demo: boolean;
  rule_notice: string;
  fight: Fight;
  analysis: {
    total_deaths: number;
    fight_duration_seconds: number;
    evidence: Evidence[];
    deaths: Death[];
  };
  coach_report: {
    source: string;
    wipe_summary: string;
    primary_causes: string[];
    priority_fixes: string[];
    player_advice: {
      player: string;
      issues: string[];
      suggestions: string[];
    }[];
  };
};
const base = (
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
).replace(/\/$/, "");
export function reportCode(input: string): string {
  const text = input.trim();
  if (/^[a-zA-Z0-9]{16}$/.test(text)) return text;
  try {
    const url = new URL(text);
    if (
      !/^https?:$/.test(url.protocol) ||
      !(
        url.hostname === "warcraftlogs.com" ||
        url.hostname.endsWith(".warcraftlogs.com")
      )
    )
      throw new Error();
    const match = url.pathname.match(/^\/reports\/([a-zA-Z0-9]{16})(?:\/|$)/);
    if (match) return match[1];
  } catch {}
  throw new Error("請貼上有效的 Warcraft Logs 戰報網址，或 16 碼報告代碼。");
}
async function request<T>(
  path: string,
  method = "GET",
  timeout = 90000,
): Promise<T> {
  try {
    const response = await fetch(`${base}/api${path}`, {
      method,
      signal: AbortSignal.timeout(timeout),
      cache: "no-store",
    });
    const data = await response.json();
    if (!response.ok)
      throw new Error(
        typeof data.detail === "string"
          ? data.detail
          : "服務暫時無法完成請求，請稍後重試。",
      );
    return data;
  } catch (error) {
    if (error instanceof TypeError)
      throw new Error(
        "無法連線到後端，請確認 make dev 已啟動、8000 port 可用。",
      );
    if (error instanceof DOMException)
      throw new Error("請求逾時，請稍後重試或選擇較短的戰鬥。");
    throw error;
  }
}
export const fetchReport = (code: string, demo: boolean) =>
  request<Report>(
    demo ? "/demo/report" : `/reports/${encodeURIComponent(code)}`,
  );
export const fetchAnalysis = (code: string, id: number, demo: boolean) =>
  request<Analysis>(
    demo
      ? `/demo/fights/${id}/analysis`
      : `/reports/${encodeURIComponent(code)}/fights/${id}/analysis`,
    "POST",
  );
export function time(ms: number) {
  const seconds = Math.floor(ms / 1000);
  return `${Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0")}:${(seconds % 60).toString().padStart(2, "0")}`;
}

export type ServiceStatusData = {
  wcl_configured: boolean;
  gemini_configured: boolean;
  demo_available: boolean;
};
export const fetchServiceStatus = () =>
  request<ServiceStatusData>("/status", "GET", 5000);
