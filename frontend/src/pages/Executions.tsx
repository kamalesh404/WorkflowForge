import { useEffect, useState } from "react";
import { cancelExecution, getExecutions, type Execution } from "../api/client";

export default function Executions() {
  const [executions, setExecutions] = useState<Execution[]>([]);

  useEffect(() => {
    getExecutions().then(setExecutions);
    const interval = setInterval(() => getExecutions().then(setExecutions), 3000);
    return () => clearInterval(interval);
  }, []);

  const handleCancel = async (id: string) => {
    await cancelExecution(id);
  };

  return (
    <div className="page">
      <h2>Executions</h2>
      {executions.length === 0 ? (
        <p className="empty">No executions yet.</p>
      ) : (
        <div className="list">
          {executions.map((ex) => (
            <div key={ex.id} className="card item">
              <div>
                <h3>{ex.workflow_name || ex.workflow_id}</h3>
                <p>
                  {ex.completed_tasks}/{ex.total_tasks} tasks
                </p>
                <span className={`badge status-${ex.status}`}>{ex.status}</span>
              </div>
              <div className="actions">
                {ex.status === "running" && (
                  <button onClick={() => handleCancel(ex.id)}>Cancel</button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
