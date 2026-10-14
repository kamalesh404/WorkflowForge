import { useEffect, useState } from "react";
import { executeWorkflow, getWorkflows, type Workflow } from "../api/client";

export default function Workflows() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);

  useEffect(() => {
    getWorkflows().then(setWorkflows);
  }, []);

  const handleExecute = async (id: string) => {
    await executeWorkflow(id);
  };

  return (
    <div className="page">
      <h2>Workflows</h2>
      {workflows.length === 0 ? (
        <p className="empty">No workflows registered yet.</p>
      ) : (
        <div className="list">
          {workflows.map((wf) => (
            <div key={wf.id} className="card item">
              <div>
                <h3>{wf.name}</h3>
                <p>{wf.description || "No description"}</p>
                <span className="badge">{wf.tasks.length} tasks</span>
              </div>
              <button onClick={() => handleExecute(wf.id)}>Execute</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
