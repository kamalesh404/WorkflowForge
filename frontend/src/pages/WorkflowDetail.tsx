import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  cancelExecution,
  executeWorkflow,
  getWorkflow,
  getWorkflowExecutions,
  getWorkflowMetrics,
  scheduleWorkflow,
  type Execution,
  type Workflow,
  type WorkflowMetrics,
} from "../api/client";

function buildDagLayout(tasks: Workflow["tasks"]) {
  const levels = new Map<string, number>();
  const visited = new Set<string>();

  function getLevel(taskId: string): number {
    if (levels.has(taskId)) return levels.get(taskId)!;
    if (visited.has(taskId)) return 0;
    visited.add(taskId);
    const task = tasks.find((t) => t.id === taskId);
    if (!task || task.dependencies.length === 0) {
      levels.set(taskId, 0);
      return 0;
    }
    const level = Math.max(...task.dependencies.map(getLevel)) + 1;
    levels.set(taskId, level);
    return level;
  }

  tasks.forEach((t) => getLevel(t.id));

  const levelGroups = new Map<number, Workflow["tasks"]>();
  tasks.forEach((t) => {
    const lvl = levels.get(t.id) ?? 0;
    if (!levelGroups.has(lvl)) levelGroups.set(lvl, []);
    levelGroups.get(lvl)!.push(t);
  });

  const maxWidth = Math.max(...[...levelGroups.values()].map((g) => g.length));
  const pos = new Map<string, { x: number; y: number }>();
  levelGroups.forEach((group, lvl) => {
    group.forEach((task, idx) => {
      pos.set(task.id, {
        x: (idx + 1) * (100 / (group.length + 1)),
        y: (lvl + 1) * (100 / (levelGroups.size + 1)),
      });
    });
  });

  return { pos, maxWidth, maxHeight: levelGroups.size };
}

function DagGraph({ workflow }: { workflow: Workflow }) {
  const { pos, maxHeight } = useMemo(() => buildDagLayout(workflow.tasks), [workflow.tasks]);

  if (workflow.tasks.length === 0) {
    return <div className="dag-empty">No tasks in this workflow.</div>;
  }

  return (
    <div className="dag-container" style={{ paddingBottom: `${Math.max(40, maxHeight * 22)}%` }}>
      <svg className="dag-edges" viewBox="0 0 100 100" preserveAspectRatio="none">
        {workflow.tasks.flatMap((task) =>
          task.dependencies.map((dep) => {
            const from = pos.get(dep);
            const to = pos.get(task.id);
            if (!from || !to) return null;
            const midX = from.x + (to.x - from.x) / 2;
            return (
              <path
                key={`${dep}-${task.id}`}
                d={`M ${from.x} ${from.y} C ${midX} ${from.y}, ${midX} ${to.y}, ${to.x} ${to.y}`}
                className="dag-edge"
                fill="none"
                vectorEffect="non-scaling-stroke"
              />
            );
          })
        )}
      </svg>
      {workflow.tasks.map((task) => {
        const p = pos.get(task.id);
        if (!p) return null;
        return (
          <div
            key={task.id}
            className="dag-node"
            style={{ left: `${p.x}%`, top: `${p.y}%` }}
          >
            <span className="dag-node-label">{task.name}</span>
            <span className="dag-node-meta">{task.dependencies.length > 0 ? `${task.dependencies.length} deps` : "root"}</span>
          </div>
        );
      })}
    </div>
  );
}

export default function WorkflowDetail() {
  const { id } = useParams<{ id: string }>();
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [metrics, setMetrics] = useState<WorkflowMetrics | null>(null);
  const [cronExpr, setCronExpr] = useState("");
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [scheduling, setScheduling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadExecutions = useCallback(async () => {
    if (!id) return;
    const ex = await getWorkflowExecutions(id);
    setExecutions(ex);
  }, [id]);

  useEffect(() => {
    if (!id) return;
    getWorkflow(id).then(setWorkflow).catch(() => setError("Workflow not found"));
    getWorkflowMetrics(id).then(setMetrics).catch(() => null);
    loadExecutions();
    const interval = setInterval(loadExecutions, 5000);
    return () => clearInterval(interval);
  }, [id, loadExecutions]);

  const handleExecute = async () => {
    if (!id) return;
    setExecuting(true);
    setError(null);
    try {
      await executeWorkflow(id);
      await loadExecutions();
    } catch {
      setError("Failed to execute workflow");
    } finally {
      setExecuting(false);
    }
  };

  const handleSchedule = async () => {
    if (!id || !cronExpr.trim()) return;
    setScheduling(true);
    setError(null);
    try {
      await scheduleWorkflow(id, cronExpr.trim());
      setScheduleOpen(false);
      setCronExpr("");
    } catch {
      setError("Failed to schedule workflow");
    } finally {
      setScheduling(false);
    }
  };

  const handleCancel = async (executionId: string) => {
    await cancelExecution(executionId);
    loadExecutions();
  };

  if (!workflow) {
    if (error) {
      return (
        <div className="page">
          <p className="empty">{error}</p>
          <Link to="/workflows" className="btn-secondary" style={{ display: "inline-block", marginTop: "1rem" }}>Back to Workflows</Link>
        </div>
      );
    }
    return <div className="page"><p className="empty">Loading...</p></div>;
  }

  const runningCount = executions.filter((e) => e.status === "running").length;

  return (
    <div className="page">
      <div className="breadcrumb">
        <Link to="/workflows">Workflows</Link>
        <span className="breadcrumb-sep">/</span>
        <span>{workflow.name}</span>
      </div>

      <div className="detail-header">
        <div>
          <h2>{workflow.name}</h2>
          <p className="text-muted">{workflow.description || "No description"}</p>
        </div>
        <div className="actions">
          <button onClick={handleExecute} disabled={executing}>
            {executing ? "Executing..." : "Execute Now"}
          </button>
          <button className="btn-secondary" onClick={() => setScheduleOpen(!scheduleOpen)}>
            Schedule
          </button>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {scheduleOpen && (
        <div className="schedule-form">
          <label htmlFor="cron-input">Cron Expression</label>
          <div className="schedule-form-row">
            <input
              id="cron-input"
              type="text"
              placeholder="0 * * * *"
              value={cronExpr}
              onChange={(e) => setCronExpr(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSchedule()}
            />
            <button onClick={handleSchedule} disabled={scheduling || !cronExpr.trim()}>
              {scheduling ? "Scheduling..." : "Apply"}
            </button>
          </div>
          <p className="text-muted-sm">Example: <code>0 * * * *</code> (every hour), <code>*/15 * * * *</code> (every 15 min)</p>
        </div>
      )}

      <div className="metrics-row">
        <div className="card metric-card">
          <span className="metric-value">{metrics?.success_rate != null ? `${(metrics.success_rate * 100).toFixed(1)}%` : "--"}</span>
          <span className="metric-label">Success Rate</span>
        </div>
        <div className="card metric-card">
          <span className="metric-value">{metrics?.avg_duration_ms != null ? `${(metrics.avg_duration_ms / 1000).toFixed(1)}s` : "--"}</span>
          <span className="metric-label">Avg Duration</span>
        </div>
        <div className="card metric-card">
          <span className="metric-value">{metrics?.total_runs ?? executions.length}</span>
          <span className="metric-label">Total Runs</span>
        </div>
        <div className="card metric-card">
          <span className="metric-value">{metrics?.failed_runs ?? executions.filter((e) => e.status === "failed").length}</span>
          <span className="metric-label">Failed Runs</span>
        </div>
        <div className="card metric-card">
          <span className="metric-value">{runningCount}</span>
          <span className="metric-label">Running</span>
        </div>
      </div>

      <div className="detail-section">
        <h3>Tasks ({workflow.tasks.length})</h3>
        <DagGraph workflow={workflow} />
      </div>

      <div className="detail-section">
        <h3>Executions ({executions.length})</h3>
        {executions.length === 0 ? (
          <p className="empty">No executions yet.</p>
        ) : (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Tasks</th>
                  <th>Started</th>
                  <th>Duration</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {executions.map((ex) => {
                  const duration = ex.started_at && ex.completed_at
                    ? Math.max(0, new Date(ex.completed_at).getTime() - new Date(ex.started_at).getTime())
                    : null;
                  return (
                    <tr key={ex.id}>
                      <td><span className={`badge status-${ex.status}`}>{ex.status}</span></td>
                      <td>{ex.completed_tasks}/{ex.total_tasks}</td>
                      <td>{ex.started_at ? new Date(ex.started_at).toLocaleTimeString() : "--"}</td>
                      <td>{duration != null ? `${(duration / 1000).toFixed(1)}s` : "--"}</td>
                      <td>
                        <div className="actions">
                          <Link to={`/executions/${ex.id}`} className="btn-link">View</Link>
                          {ex.status === "running" && (
                            <button className="btn-danger" onClick={() => handleCancel(ex.id)}>Cancel</button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
