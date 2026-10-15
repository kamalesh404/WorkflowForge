import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { connectWebSocket, getStats, type Stats } from "../api/client";

const breadcrumbLabels: Record<string, string> = {
  "/": "Dashboard",
  "/workflows": "Workflows",
  "/executions": "Executions",
};

function getBreadcrumbs(pathname: string): Array<{ label: string; path: string }> {
  const crumbs: Array<{ label: string; path: string }> = [];
  const parts = pathname.split("/").filter(Boolean);

  if (parts[0] === "workflows") {
    crumbs.push({ label: "Workflows", path: "/workflows" });
    if (parts[1]) {
      crumbs.push({ label: `Workflow`, path: `/workflows/${parts[1]}` });
    }
  } else if (parts[0] === "executions") {
    crumbs.push({ label: "Executions", path: "/executions" });
    if (parts[1]) {
      crumbs.push({ label: "Execution", path: `/executions/${parts[1]}` });
    }
  } else if (parts.length === 0) {
    crumbs.push({ label: breadcrumbLabels["/"] || "Dashboard", path: "/" });
  }

  return crumbs;
}

export default function Layout() {
  const location = useLocation();
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

  const breadcrumbs = getBreadcrumbs(location.pathname);

  return (
    <div className="layout">
      <aside className="sidebar">
        <h1 className="logo">WorkflowForge</h1>
        <nav>
          <NavLink to="/" end>
            Dashboard
          </NavLink>
          <NavLink to="/workflows">Workflows</NavLink>
          <NavLink to="/executions">Executions</NavLink>
        </nav>
      </aside>
      <div className="main-area">
        <header className="topbar">
          <nav className="breadcrumbs">
            {breadcrumbs.map((crumb, idx) => (
              <span key={crumb.path} className="breadcrumb-item">
                {idx > 0 && <span className="breadcrumb-sep">/</span>}
                <span className={idx === breadcrumbs.length - 1 ? "breadcrumb-current" : ""}>
                  {crumb.label}
                </span>
              </span>
            ))}
          </nav>
          <div className="global-stats">
            <span className="global-stat">
              <span className="global-stat-value text-success">{stats.completed}</span>
              <span className="global-stat-label">Completed</span>
            </span>
            <span className="global-stat">
              <span className="global-stat-value text-warning">{stats.running}</span>
              <span className="global-stat-label">Running</span>
            </span>
            <span className="global-stat">
              <span className="global-stat-value text-danger">{stats.failed}</span>
              <span className="global-stat-label">Failed</span>
            </span>
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
