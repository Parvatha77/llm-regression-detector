import { useEffect, useState, useRef, useMemo } from "react";
import axios from "axios";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
} from "recharts";

const REFRESH_MS = 6000;
const STORAGE_KEY = "regression-dashboard-snapshot";
const CONFIG_STORAGE_KEY = "regression-dashboard-config";

function resolveApiUrl() {
  try {
    const stored = JSON.parse(
      sessionStorage.getItem(CONFIG_STORAGE_KEY) || "{}"
    );
    if (stored?.apiUrl) return stored.apiUrl;
  } catch {}
  if (window.__VITE_API_URL__) return window.__VITE_API_URL__;
  if (import.meta.env?.VITE_API_URL) return import.meta.env.VITE_API_URL;
  return "http://localhost:8000/api";
}

function setStoredApiUrl(url) {
  try {
    sessionStorage.setItem(
      CONFIG_STORAGE_KEY,
      JSON.stringify({ apiUrl: url, updatedAt: new Date().toISOString() })
    );
  } catch {}
}

function StatusBadge({ status }) {
  const colors = { ok: "#2e7d32", warning: "#f9a825", critical: "#c62828" };
  return (
    <span
      style={{
        background: colors[status] || "#999",
        color: "white",
        padding: "4px 12px",
        borderRadius: 12,
        fontSize: 13,
        fontWeight: 600,
        textTransform: "uppercase",
      }}
    >
      {status}
    </span>
  );
}

function CaseRow({ c }) {
  const [showDetails, setShowDetails] = useState(false);
  return (
    <>
      <tr key={c.case_id} style={{ borderBottom: "1px solid #eee" }}>
        <td style={{ padding: 8 }}>{c.case_id}</td>
        <td style={{ padding: 8 }}>{c.input}</td>
        <td style={{ padding: 8 }}>{c.old_output ?? "-"}</td>
        <td style={{ padding: 8 }}>{c.new_output ?? "-"}</td>
      </tr>
      {showDetails && (
        <tr key={`${c.case_id}-details`} style={{ background: "#fafafa" }}>
          <td colSpan={4} style={{ padding: 8 }}>
            <details open style={{ marginTop: 4 }}>
              <summary style={{ cursor: "pointer", color: "#1976d2" }}>
                View full case payload
              </summary>
              <pre
                style={{
                  background: "#f5f5f5",
                  border: "1px solid #ddd",
                  padding: 12,
                  borderRadius: 6,
                  fontSize: 12,
                  marginTop: 8,
                  overflow: "auto",
                  maxHeight: 240,
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                }}
              >
                {JSON.stringify(c, null, 2)}
              </pre>
            </details>
          </td>
        </tr>
      )}
    </>
  );
}

function CaseTable({ title, cases }) {
  if (!cases?.length)
    return <p style={{ color: "#777" }}>No {title.toLowerCase()}.</p>;
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: 24 }}>
      <thead>
        <tr style={{ background: "#f0f0f0", textAlign: "left" }}>
          <th style={{ padding: 8 }}>Case ID</th>
          <th style={{ padding: 8 }}>Input</th>
          <th style={{ padding: 8 }}>Old</th>
          <th style={{ padding: 8 }}>New</th>
        </tr>
      </thead>
      <tbody>
        {cases.map((c) => (
          <CaseRow key={c.case_id} c={c} />
        ))}
      </tbody>
    </table>
  );
}

function fillMissingOutputs(cases, runs) {
  if (!cases) return cases;
  const map = new Map();
  for (const run of runs ?? []) {
    if (!run.cases) continue;
    for (const c of run.cases) {
      map.set(`${run.run_id}:${c.case_id}`, c.output);
    }
  }
  return cases.map((c) => ({
    ...c,
    old_output:
      c.old_output ??
      map.get(`${c.baseline_run_id}:${c.case_id}`) ??
      null,
  }));
}

export default function App() {
  const [runs, setRuns] = useState([]);
  const [rawComparison, setRawComparison] = useState(null);
  const [drift, setDrift] = useState(null);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [connected, setConnected] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [apiUrl, setApiUrl] = useState(resolveApiUrl());
  const mountedRef = useRef(true);
  const refreshTimerRef = useRef(null);

  useEffect(() => {
    mountedRef.current = true;
    let firstRun = true;

    async function refresh() {
      if (!mountedRef.current) return;
      if (!firstRun) setUpdating(true);
      try {
        const runsRes = await axios.get(`${apiUrl}/runs`);
        const runs = runsRes.data;

        const [comparisonRes, driftRes] = await Promise.all([
          axios.get(`${apiUrl}/comparison/latest`),
          axios.get(`${apiUrl}/drift`),
        ]);

        const snapshot = {
          runs,
          comparison: comparisonRes.data,
          drift: driftRes.data,
          fetchedAt: new Date().toISOString(),
        };
        try {
          sessionStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
        } catch {}

        if (mountedRef.current) {
          setRuns(runs);
          setRawComparison(comparisonRes.data);
          setDrift(driftRes.data);
          setError(null);
          setLastUpdated(new Date().toLocaleTimeString());
          setConnected(true);
          setUpdating(false);
        }
      } catch (err) {
        if (mountedRef.current) {
          setError(
            err.message || "Backend not reachable - is uvicorn running?"
          );
          setConnected(false);
          setUpdating(false);
        }
      }
      firstRun = false;
    }

    refresh();
    refreshTimerRef.current = setInterval(refresh, REFRESH_MS);
    return () => {
      mountedRef.current = false;
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current);
      }
    };
  }, [apiUrl]);

  const savedApiUrl = useMemo(() => resolveApiUrl(), []);
  useEffect(() => {
    if (apiUrl !== savedApiUrl) {
      setStoredApiUrl(apiUrl);
      window.location.reload();
    }
  }, [apiUrl, savedApiUrl]);

  const comparison = useMemo(
    () =>
      rawComparison
        ? {
            ...rawComparison,
            regressions: fillMissingOutputs(rawComparison.regressions, runs),
            improvements: fillMissingOutputs(
              rawComparison.improvements,
              runs
            ),
          }
        : null,
    [rawComparison, runs]
  );

  if (error && !runs.length && !connected) {
    return (
      <div style={{ padding: 40, fontFamily: "sans-serif" }}>
        {error}
        <button
          style={{ marginTop: 12, padding: "6px 12px" }}
          onClick={() => window.location.reload()}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div style={{ fontFamily: "sans-serif", maxWidth: 960, margin: "40px auto", padding: 20 }}>
      <div style={{ marginBottom: 16 }}>
        <h1>Model Regression Dashboard</h1>
        <div
          style={{
            marginTop: 8,
            display: "flex",
            gap: 12,
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >
          <label style={{ fontSize: 13 }}>
            Backend:
            <input
              type="text"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value.trim())}
              style={{
                marginLeft: 6,
                padding: "2px 6px",
                border: "1px solid #ccc",
                borderRadius: 4,
                fontFamily: "monospace",
                fontSize: 12,
              }}
            />
          </label>
          <span style={{ fontSize: 12, color: "#777" }}>
            {updating ? "updating..." : `last updated ${lastUpdated ?? "-"}`}
          </span>
          <span
            style={{
              fontSize: 12,
              color: connected ? "#2e7d32" : "#c62828",
            }}
          >
            {connected ? "connected" : "offline"}
          </span>
        </div>
      </div>

      {comparison && (
        <div style={{ marginBottom: 32 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
            <StatusBadge status={comparison.status} />
            <span>
              {comparison.baseline_run_id} to {comparison.current_run_id}
            </span>
          </div>
          <p>
            Pass rate delta: <strong>{(comparison.pass_rate_delta * 100).toFixed(2)}%</strong>
            {" · "}
            Regressions: <strong>{comparison.regressions.length}</strong>
            {" · "}
            Improvements: <strong>{comparison.improvements.length}</strong>
          </p>
        </div>
      )}

      {drift?.drift_detected && (
        <div
          style={{
            background: "#fff3cd",
            border: "1px solid #f9a825",
            padding: 12,
            borderRadius: 8,
            marginBottom: 24,
          }}
        >
          Warning: Slow drift detected - pass rate dropped{" "}
          {(drift.drop * 100).toFixed(2)}% over the last 7 runs.
        </div>
      )}

      <h2>Trend (last {runs.length} runs)</h2>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={runs}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="run_id" tick={{ fontSize: 10 }} />
          <YAxis
            domain={[0, 1]}
            tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
          />
          <Tooltip formatter={(v) => `${(v * 100).toFixed(2)}%`} />
          <Line
            type="monotone"
            dataKey="pass_rate"
            stroke="#1976d2"
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>

      {comparison && (
        <>
          <h2>Regressions</h2>
          <CaseTable title="Regressions" cases={comparison.regressions} />
          <h2>Improvements</h2>
          <CaseTable title="Improvements" cases={comparison.improvements} />
        </>
      )}
    </div>
  );
}
