import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { connectWebSocket, getExecutions, getStats, type Execution, type Stats } from "../api/client";

export default function Dashboard() {
  const [stats, setStats] = useState<Stats>({
    total_workflows: 0,
    total_executions: 0,
    running: 0,
    completed: 0,
    failed: 0,
  });
  const [recentExecutions, setRecentExecutions] = useState<Execution[]>([]);

  useEffect(() => {
    getStats().then(setStats);
    const ws = connectWebSocket(setStats);
    return () => ws.close();
  }, []);

  useEffect(() => {
    getExecutions().then((ex) => setRecentExecutions(ex.slice(0, 10)));
    const interval = setInterval(async () => {
      const ex = await getExecutions();
      setRecentExecutions(ex.slice(0, 10));
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const successRate = stats.total_executions > 0
    ? ((stats.completed / stats.total_executions) * 100).toFixed(1)
    : "0.0";

  const avgTime = recentExecutions.length > 0
    ? recentExecutions.reduce((acc, ex) => {
        if (ex.started_at && ex.completed_at) {
          return acc + (new Date(ex.completed_at).getTime() - new Date(ex.started_at).getTime());
        }
        return acc;
      }, 0) / recentExecutions.filter((e) => e.started_at && e.completed_at).length || 0
    : 0;

  return (
    <div className="page">
      <h2>Dashboard</h2>
      <div className="grid">
        <div className="card stat">
          <span className="stat-value">{stats.total_workflows}</span>
          <span className="stat-label">Workflows</span>
        </div>
        <div className="card stat">
          <span className="stat-value">{stats.total_executions}</span>
          <span className="stat-label">Total Executions</span>
        </div>
        <div className="card stat running">
          <span className="stat-value">{stats.running}</span>
          <span className="stat-label">Running</span>
        </div>
        <div className="card stat completed">
          <span className="stat-value">{stats.completed}</span>
          <span className="stat-label">Completed</span>
        </div>
        <div className="card stat failed">
          <span className="stat-value">{stats.failed}</span>
          <span className="stat-label">Failed</span>
        </div>
        <div className="card stat success-rate">
          <span className="stat-value">{successRate}%</span>
          <span className="stat-label">Success Rate</span>
        </div>
        <div className="card stat avg-time">
          <span className="stat-value">{avgTime > 0 ? `${(avgTime / 1000).toFixed(1)}s` : "--"}</span>
          <span className="stat-label">Avg Execution Time</span>
        </div>
      </div>

      <div className="quick-actions">
        <Link to="/workflows" className="quick-action-card card">
          <span className="quick-action-title">Create Workflow</span>
          <span className="quick-action-desc">Define and register a new workflow</span>
        </Link>
        <Link to="/executions" className="quick-action-card card">
          <span className="quick-action-title">View All Executions</span>
          <span className="quick-action-desc">Monitor and manage execution runs</span>
        </Link>
      </div>

      <div className="detail-section">
        <h3>Recent Executions</h3>
        {recentExecutions.length === 0 ? (
          <p className="empty">No executions yet.</p>
        ) : (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Workflow</th>
                  <th>Status</th>
                  <th>Tasks</th>
                  <th>Started</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {recentExecutions.map((ex) => (
                  <tr key={ex.id}>
                    <td>{ex.workflow_name || ex.workflow_id}</td>
                    <td><span className={`badge status-${ex.status}`}>{ex.status}</span></td>
                    <td>{ex.completed_tasks}/{ex.total_tasks}</td>
                    <td>{ex.started_at ? new Date(ex.started_at).toLocaleTimeString() : "--"}</td>
                    <td>
                      <Link to={`/executions/${ex.id}`} className="btn-link">View</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
