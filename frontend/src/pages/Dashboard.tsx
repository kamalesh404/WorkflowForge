import { useEffect, useState } from "react";
import { connectWebSocket, getStats, type Stats } from "../api/client";

export default function Dashboard() {
  const [stats, setStats] = useState<Stats>({
    total_workflows: 0,
    total_executions: 0,
    running: 0,
    completed: 0,
    failed: 0,
  });

  useEffect(() => {
    getStats().then(setStats);
    const ws = connectWebSocket(setStats);
    return () => ws.close();
  }, []);

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
      </div>
    </div>
  );
}
