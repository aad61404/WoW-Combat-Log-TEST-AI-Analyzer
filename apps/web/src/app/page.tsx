"use client";

import { FormEvent, useState } from "react";
import ServiceStatus from "@/components/ServiceStatus";
import {
  Analysis,
  Report,
  fetchAnalysis,
  fetchReport,
  reportCode,
  time,
} from "@/lib/api";

const names: Record<string, string> = {
  death: "玩家死亡",
  mechanic_fail: "機制命中",
  missed_interrupt: "未打斷施法",
  debuff_stack_exceeded: "Debuff 疊層",
};
export default function Home() {
  const [input, setInput] = useState("");
  const [report, setReport] = useState<Report | null>(null);
  const [result, setResult] = useState<Analysis | null>(null);
  const [demo, setDemo] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all");
  async function load(useDemo: boolean) {
    setError("");
    try {
      const code = useDemo ? "demo" : reportCode(input);
      setBusy("正在讀取戰報…");
      const data = await fetchReport(code, useDemo);
      setReport(data);
      setDemo(useDemo);
      setResult(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "讀取失敗，請重試。");
    } finally {
      setBusy("");
    }
  }
  async function analyze(id: number) {
    if (!report) return;
    setError("");
    setBusy(
      demo ? "正在分析範例戰鬥…" : "正在讀取事件並產生報告，可能需要一些時間…",
    );
    try {
      setResult(await fetchAnalysis(report.code, id, demo));
      setFilter("all");
    } catch (e) {
      setError(e instanceof Error ? e.message : "分析失敗，請重試。");
    } finally {
      setBusy("");
    }
  }
  function reset() {
    setReport(null);
    setResult(null);
    setError("");
  }
  function submit(e: FormEvent) {
    e.preventDefault();
    void load(false);
  }
  const stage = result ? 3 : report ? 2 : 1;
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <button className="brand" onClick={reset} disabled={!!busy}>
          <span className="brand-icon">W</span>
          <span>
            WIPE<span className="brand-light">WISE</span>
            <small>COMBAT LOG ANALYZER</small>
          </span>
        </button>
        <div className="nav-label">WORKSPACE</div>
        <button className="nav-item active" onClick={reset} disabled={!!busy}>
          <span>◈</span> 戰報分析 <span className="nav-arrow">↗</span>
        </button>
        <div className="sidebar-guide">
          <span className="eyebrow">從紀錄到下一次突破</span>
          <p>
            還原關鍵時刻，
            <br />
            讓每一次嘗試都有收穫。
          </p>
          <div className="tiny-line" />
          <small>
            事件分析 · 死亡時間線
            <br />
            中文教練報告
          </small>
        </div>
        <div className="sidebar-footer">
          <span className="status-dot" /> 本機開發版 <span>v0.1</span>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span>
            工作台 <span className="slash">/</span> <strong>戰報分析</strong>
          </span>
          <span className="version">MVP PREVIEW</span>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <div className="eyebrow">RAID REVIEW</div>
              <h1>
                {result
                  ? "把失敗，變成下一次的優勢。"
                  : "每一場戰鬥，都有答案。"}
              </h1>
              <p>從戰鬥紀錄找出關鍵事件，為下一次開打做好準備。</p>
            </div>
            <span className="heading-mark">↗</span>
          </div>
          <ol className="steps">
            {["匯入戰報", "選擇戰鬥", "檢視分析"].map((label, i) => (
              <li
                key={label}
                className={
                  stage === i + 1 ? "current" : stage > i + 1 ? "complete" : ""
                }
              >
                <span>{stage > i + 1 ? "✓" : `0${i + 1}`}</span>
                {label}
              </li>
            ))}
          </ol>
          {error && (
            <div role="alert" className="error">
              {error}
              <button onClick={() => setError("")} aria-label="關閉錯誤訊息">
                ×
              </button>
            </div>
          )}
          {busy && (
            <div className="loading" role="status">
              <span className="spinner" />
              {busy}
            </div>
          )}
          {!report && (
            <>
              <ServiceStatus />
              <section className="import-card">
                <div className="card-heading">
                  <span className="square-icon">↗</span>
                  <div>
                    <h2>匯入你的戰報</h2>
                    <p>貼上 Warcraft Logs 公開報告，開始回顧這場戰鬥。</p>
                  </div>
                </div>
                <form onSubmit={submit}>
                  <label htmlFor="report-url">WARCRAFT LOGS 網址</label>
                  <div className="input-row">
                    <input
                      id="report-url"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder="https://www.warcraftlogs.com/reports/…"
                      disabled={!!busy}
                      autoComplete="off"
                    />
                    <button
                      className="primary"
                      disabled={!!busy || !input.trim()}
                    >
                      讀取戰報 <span>→</span>
                    </button>
                  </div>
                  <p className="hint">
                    支援公開戰報網址或 16 碼報告代碼。真實分析需先設定 WCL API
                    憑證。
                  </p>
                </form>
                <div className="demo-row">
                  <div>
                    <span className="pill purple">DEMO</span>
                    <strong>還沒有戰報？先體驗範例。</strong>
                    <p>使用內建戰鬥資料，探索完整分析流程。</p>
                  </div>
                  <button
                    className="secondary"
                    disabled={!!busy}
                    onClick={() => load(true)}
                  >
                    開啟範例戰報 ↗
                  </button>
                </div>
              </section>
              <div className="features">
                {[
                  [
                    "01",
                    "還原死亡前的 5 秒",
                    "依序查看傷害來源與致命一擊，找到最需要回顧的時刻。",
                  ],
                  [
                    "02",
                    "讓判斷有跡可循",
                    "時間線保留事件與數值，示範規則會清楚標示資料限制。",
                  ],
                  [
                    "03",
                    "整理下一場的重點",
                    "設定 Gemini 後產生中文教練報告；未設定時提供紀錄摘要。",
                  ],
                ].map(([n, title, desc]) => (
                  <article key={n}>
                    <span className="feature-number">{n}</span>
                    <h3>{title}</h3>
                    <p>{desc}</p>
                  </article>
                ))}
              </div>
            </>
          )}
          {report && !result && (
            <section className="report-section">
              <div className="section-title">
                <div>
                  <span className="eyebrow">
                    {demo ? "DEMO REPORT" : "WARCRAFT LOGS"}
                  </span>
                  <h2>{report.title}</h2>
                  <p>
                    {report.owner} ·{" "}
                    {report.actors.filter((a) => a.type === "Player").length}{" "}
                    位玩家 · {report.fights.length} 場戰鬥
                  </p>
                </div>
                <button
                  className="text-button"
                  disabled={!!busy}
                  onClick={reset}
                >
                  ← 更換戰報
                </button>
              </div>
              {demo && (
                <div className="notice">
                  範例模式 · 僅第 1 場具備事件資料，不會呼叫外部 API。
                </div>
              )}
              {!report.fights.length && (
                <p className="empty">
                  此報告沒有可分析的 Boss 戰鬥，請更換戰報。
                </p>
              )}
              <div className="fight-list">
                {report.fights.map((f) => (
                  <article className="fight-card" key={f.id}>
                    <div className="fight-emblem">{f.name.slice(0, 1)}</div>
                    <div className="fight-info">
                      <span className="eyebrow">
                        PULL {String(f.id).padStart(2, "0")}
                      </span>
                      <h3>{f.name}</h3>
                      <p>
                        {time(f.end_time - f.start_time)} <span>·</span>{" "}
                        {f.kill
                          ? "Boss 已擊殺"
                          : `Boss 剩餘 ${f.fight_percentage ?? "—"}%`}
                      </p>
                    </div>
                    <span className={`pill ${f.kill ? "green" : "red"}`}>
                      {f.kill ? "KILL" : "WIPE"}
                    </span>
                    <button
                      className="primary"
                      disabled={!!busy}
                      onClick={() => analyze(f.id)}
                    >
                      分析戰鬥 →
                    </button>
                  </article>
                ))}
              </div>
            </section>
          )}
          {result && (
            <>
              <div className="section-title">
                <div>
                  <span className="eyebrow">
                    {result.demo ? "DEMO ANALYSIS" : "FIGHT ANALYSIS"}
                  </span>
                  <h2>
                    {result.fight.name}{" "}
                    <span
                      className={`pill ${result.fight.kill ? "green" : "red"}`}
                    >
                      {result.fight.kill ? "KILL" : "WIPE"}
                    </span>
                  </h2>
                </div>
                <button
                  className="text-button"
                  onClick={() => {
                    setResult(null);
                    setError("");
                  }}
                >
                  ← 返回戰鬥列表
                </button>
              </div>
              <div className="notice">{result.rule_notice}</div>
              <div className="stats">
                <div>
                  <span>戰鬥時長</span>
                  <strong>
                    {time(result.analysis.fight_duration_seconds * 1000)}
                  </strong>
                </div>
                <div>
                  <span>死亡次數</span>
                  <strong className="red-text">
                    {result.analysis.total_deaths}
                    <small> 次</small>
                  </strong>
                </div>
                <div>
                  <span>記錄事件</span>
                  <strong>
                    {result.analysis.evidence.length}
                    <small> 筆</small>
                  </strong>
                </div>
                <div>
                  <span>報告來源</span>
                  <strong className="source-label">
                    {result.coach_report.source === "ai"
                      ? "AI 教練"
                      : "紀錄摘要"}
                  </strong>
                </div>
              </div>
              <div className="analysis-grid">
                <section className="panel">
                  <div className="panel-title">
                    <h3>戰鬥時間線</h3>
                    <span className="eyebrow">TIMELINE</span>
                  </div>
                  <div className="filters">
                    {[
                      ["all", "全部事件"],
                      ["death", "玩家死亡"],
                      ["mechanic", "機制事件"],
                    ].map(([v, label]) => (
                      <button
                        key={v}
                        aria-pressed={filter === v}
                        className={filter === v ? "selected" : ""}
                        onClick={() => setFilter(v)}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  <div className="timeline">
                    {result.analysis.evidence
                      .filter(
                        (e) =>
                          filter === "all" ||
                          (filter === "death"
                            ? e.type === "death"
                            : e.type !== "death"),
                      )
                      .map((e, i) => {
                        const death =
                          e.type === "death"
                            ? result.analysis.deaths.find(
                                (d) =>
                                  d.player === e.player &&
                                  d.player_id === e.player_id &&
                                  d.timestamp === e.timestamp,
                              )
                            : null;
                        return (
                          <article
                            className={`event ${e.severity}`}
                            key={`${e.timestamp}-${i}`}
                          >
                            <time>{time(e.timestamp)}</time>
                            <div className="event-body">
                              <span
                                className={`event-tag ${e.type === "death" ? "red-text" : "amber-text"}`}
                              >
                                {names[e.type] || e.type}
                                {e.type !== "death" && e.player
                                  ? ` · ${e.player}`
                                  : ""}
                              </span>
                              <p>{e.description}</p>
                              {death && (
                                <details>
                                  <summary>
                                    查看死前 5 秒傷害 ·{" "}
                                    {death.damage_taken_last_5s.length} 筆
                                  </summary>
                                  <div className="damage-list">
                                    {death.damage_taken_last_5s.length ? (
                                      death.damage_taken_last_5s.map((d, j) => (
                                        <div key={j}>
                                          <span>
                                            {time(d.timestamp)}{" "}
                                            <b>{d.ability}</b>
                                            <small>{d.source}</small>
                                          </span>
                                          <strong>
                                            {d.amount.toLocaleString()}
                                          </strong>
                                        </div>
                                      ))
                                    ) : (
                                      <p>此時間範圍內沒有傷害紀錄。</p>
                                    )}
                                  </div>
                                </details>
                              )}
                            </div>
                          </article>
                        );
                      })}
                    {!result.analysis.evidence.some(
                      (e) =>
                        filter === "all" ||
                        (filter === "death"
                          ? e.type === "death"
                          : e.type !== "death"),
                    ) && <p className="empty">此分類沒有事件。</p>}
                  </div>
                </section>
                <section className="panel coach">
                  <div className="panel-title">
                    <h3>
                      {result.coach_report.source === "ai"
                        ? "中文教練報告"
                        : "戰鬥紀錄摘要"}
                    </h3>
                    <span className="pill purple">
                      {result.coach_report.source === "ai" ? "GEMINI" : "AUTO"}
                    </span>
                  </div>
                  <p className="coach-summary">
                    {result.coach_report.wipe_summary}
                  </p>
                  <h4>值得回顧的事件</h4>
                  <ul>
                    {result.coach_report.primary_causes.map((c, i) => (
                      <li key={i}>{c}</li>
                    ))}
                  </ul>
                  <div className="priority">
                    <span className="eyebrow">NEXT PULL</span>
                    <h4>下一場優先檢視</h4>
                    <ul>
                      {result.coach_report.priority_fixes.map((c, i) => (
                        <li key={i}>{c}</li>
                      ))}
                    </ul>
                  </div>
                  <h4>個別玩家紀錄</h4>
                  {result.coach_report.player_advice.map((p, i) => (
                    <details className="player-advice" key={i}>
                      <summary>
                        {p.player}
                        <span>{p.issues.length} 筆紀錄</span>
                      </summary>
                      <ul>
                        {p.issues.map((x, j) => (
                          <li key={j}>{x}</li>
                        ))}
                      </ul>
                      {p.suggestions.map((x, j) => (
                        <p key={j}>{x}</p>
                      ))}
                    </details>
                  ))}
                  {!result.coach_report.player_advice.length && (
                    <p className="hint">沒有個別玩家建議。</p>
                  )}
                </section>
              </div>
            </>
          )}
          <footer className="page-footer">
            <span>
              WIPEWISE <span className="muted">/</span>{" "}
              每次回顧，都是下一場的起點。
            </span>
            <span>Powered by Warcraft Logs · Gemini</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
