"use client";

import { useEffect, useState } from "react";
import { fetchServiceStatus, ServiceStatusData } from "@/lib/api";

export default function ServiceStatus() {
  const [status, setStatus] = useState<ServiceStatusData | null>(null);
  const [error, setError] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    fetchServiceStatus()
      .then(
        (data) => {
          if (active) {
            setStatus(data);
            setError(false);
          }
        },
        () => {
          if (active) setError(true);
        },
      )
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [refresh]);
  return (
    <section className="service-status" aria-label="服務設定狀態">
      <div aria-live="polite">
        <strong>
          {loading ? "檢查本機服務…" : error ? "無法取得後端狀態" : "服務設定"}
        </strong>
        {!loading && !error && status && (
          <>
            <span
              className={`pill ${status.wcl_configured ? "green" : "purple"}`}
            >
              WCL · {status.wcl_configured ? "已設定" : "未設定"}
            </span>
            <span
              className={`pill ${status.gemini_configured ? "green" : "purple"}`}
            >
              Gemini · {status.gemini_configured ? "已設定" : "使用紀錄摘要"}
            </span>
            <p>
              {status.wcl_configured
                ? "憑證已載入；讀取戰報時才會驗證外部連線。"
                : "目前可使用範例模式。真實戰報需要在 .env 填入 WCL 憑證並重啟後端。"}
            </p>
          </>
        )}
        {error && !loading && <p>請確認 make dev 已啟動，再重新檢查。</p>}
      </div>
      <button
        type="button"
        className="text-button"
        disabled={loading}
        onClick={() => {
          setLoading(true);
          setRefresh((value) => value + 1);
        }}
      >
        重新檢查
      </button>
    </section>
  );
}
