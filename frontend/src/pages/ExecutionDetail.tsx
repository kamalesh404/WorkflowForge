import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  cancelExecution,
  getExecution,
  getExecutionLogs,
  type Execution,
  type ExecutionLog,
} from "../api/client";

function formatDuration(started: string | null, completed: string | null): string {
  if (!started || !completed) return "--";
  const ms = Math.max(0, new Date(completed).getTime() - new Date(started).getTime());
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function TaskTimeline({ execution }: { execution: Execution }) {
  const tasks = Object.values(execution.task_results);
  const sorted = [...tasks].sort((a, b) => {
    const aTime = a.started_at ? new Date(a.started_at).getTime() : 0;
    const bTime = b.started_at ? new Date(b.started_at).getTime() : 0;
    return aTime - bTime;
  });

  if (sorted.length === 0) {
    return <p className="empty">No task results available.</p>;
  }

  return (
    <div className="timeline">
      {sorted.map((task, idx) => (
        <div key={task.task_id} className={`timeline-item status-${task.status}`}>
          <div className="timeline-marker" />
          <div className="timeline-content">
            <div className="timeline-header">
              <span className="timeline-task-name">{task.task_name}</span>
              <span className={`badge status-${task.status}`}>{task.status}</span>
            </div>
            <div className="timeline-meta">
              <span>Duration: {formatDuration(task.started_at, task.completed_at)}</span>
              <span>Attempts: {task.attempts}</span>
              {task.started_at && <span>Started: {new Date(task.started_at).toLocaleTimeString()}</span>}
            </div>
            {task.error && (
              <div className="timeline-error">{task.error}</div>
            )}
            {task.output != null && (
              <pre className="timeline-output">{typeof task.output === "string" ? task.output : JSON.stringify(task.output, null, 2)}</pre>
            )}
          </div>
          {idx < sorted.length - 1 && <div className="timeline-connector" />}
        </div>
      ))}
    </div>
  );
}

export default function ExecutionDetail() {
  const { id } = useParams<{ id: string }>();
  const [execution, setExecution] = useState<Execution | null>(null);
  const [logs, setLogs] = useState<ExecutionLog[]>([]);
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"timeline" | "logs">("timeline");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadExecution = useCallback(async () => {
    if (!id) return;
    try {
      const ex = await getExecution(id);
      setExecution(ex);
      return ex;
    } catch {
      setError("Execution not found");
      return null;
    }
  }, [id]);

  const loadLogs = useCallback(async () => {
    if (!id) return;
    try {
      const lg = await getExecutionLogs(id);
      setLogs(lg);
    } catch {
      // logs endpoint may not be available yet
    }
  }, [id]);

  useEffect(() => {
    if (!id) return;
    loadExecution();
    loadLogs();

    const poll = async () => {
      const ex = await loadExecution();
      if (ex && ex.status === "running") {
        loadLogs();
      }
    };

    intervalRef.current = setInterval(poll, 2000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [id, loadExecution, loadLogs]);

  useEffect(() => {
    if (execution && execution.status !== "running" && intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, [execution]);

  const handleCancel = async () => {
    if (!id) return;
    setCancelling(true);
    try {
      await cancelExecution(id);
      await loadExecution();
    } catch {
      setError("Failed to cancel execution");
    } finally {
      setCancelling(false);
    }
  };

  if (!execution) {
    if (error) {
      return (
        <div className="page">
          <p className="empty">{error}</p>
          <Link to="/executions" className="btn-secondary" style={{ display: "inline-block", marginTop: "1rem" }}>Back to Executions</Link>
        </div>
      );
    }
    return <div className="page"><p className="empty">Loading...</p></div>;
  }

  const isRunning = execution.status === "running";

  return (
    <div className="page">
      <div className="breadcrumb">
        <Link to="/executions">Executions</Link>
        <span className="breadcrumb-sep">/</span>
        <span>{execution.id.slice(0, 8)}</span>
      </div>

      <div className="detail-header">
        <div>
          <h2>{execution.workflow_name || execution.workflow_id}</h2>
          <p className="text-muted">
            Execution {execution.id.slice(0, 8)} - {execution.completed_tasks}/{execution.total_tasks} tasks
          </p>
        </div>
        <div className="actions">
          <span className={`badge status-${execution.status} badge-lg`}>{execution.status}</span>
          {isRunning && (
            <button className="btn-danger" onClick={handleCancel} disabled={cancelling}>
              {cancelling ? "Cancelling..." : "Cancel Execution"}
            </button>
          )}
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="metrics-row">
        <div className="card metric-card">
          <span className="metric-value">{execution.total_tasks}</span>
          <span className="metric-label">Total Tasks</span>
        </div>
        <div className="card metric-card">
          <span className="metric-value">{execution.completed_tasks}</span>
          <span className="metric-label">Completed</span>
        </div>
        <div className="card metric-card">
          <span className="metric-value">{formatDuration(execution.started_at, execution.completed_at)}</span>
          <span className="metric-label">Duration</span>
        </div>
        <div className="card metric-card">
          <span className="metric-value">{execution.started_at ? new Date(execution.started_at).toLocaleTimeString() : "--"}</span>
          <span className="metric-label">Started</span>
        </div>
        <div className="card metric-card">
          <span className="metric-value">{execution.completed_at ? new Date(execution.completed_at).toLocaleTimeString() : "--"}</span>
          <span className="metric-label">Completed</span>
        </div>
      </div>

      <div className="tabs">
        <button
          className={`tab ${activeTab === "timeline" ? "active" : ""}`}
          onClick={() => setActiveTab("timeline")}
        >
          Timeline
        </button>
        <button
          className={`tab ${activeTab === "logs" ? "active" : ""}`}
          onClick={() => setActiveTab("logs")}
        >
          Logs ({logs.length})
        </button>
      </div>

      {activeTab === "timeline" ? (
        <TaskTimeline execution={execution} />
      ) : (
        <div className="card logs-panel">
          {logs.length === 0 ? (
            <p className="empty">No logs available.</p>
          ) : (
            <div className="logs-list">
              {logs.map((log, idx) => (
                <div key={idx} className={`log-entry log-${log.level}`}>
                  <span className="log-timestamp">{new Date(log.timestamp).toLocaleTimeString()}</span>
                  <span className="log-level">[{log.level.toUpperCase()}]</span>
                  <span className="log-task">{log.task_name}</span>
                  <span className="log-message">{log.message}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
