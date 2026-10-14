const BASE = "/api";

export interface Stats {
  total_workflows: number;
  total_executions: number;
  running: number;
  completed: number;
  failed: number;
}

export interface TaskResult {
  task_id: string;
  task_name: string;
  status: string;
  output: unknown;
  error: string | null;
  attempts: number;
  started_at: string | null;
  completed_at: string | null;
}

export interface Execution {
  id: string;
  workflow_id: string;
  workflow_name: string;
  status: string;
  task_results: Record<string, TaskResult>;
  started_at: string | null;
  completed_at: string | null;
  total_tasks: number;
  completed_tasks: number;
}

export interface Workflow {
  id: string;
  name: string;
  description: string;
  tasks: Array<{
    id: string;
    name: string;
    dependencies: string[];
    retries: number;
    retry_delay: number;
    timeout: number | null;
    params: Record<string, unknown>;
  }>;
  created_at: string;
}

export async function getStats(): Promise<Stats> {
  const res = await fetch(`${BASE}/stats`);
  return res.json();
}

export async function getWorkflows(): Promise<Workflow[]> {
  const res = await fetch(`${BASE}/workflows`);
  return res.json();
}

export async function getExecutions(workflowId?: string): Promise<Execution[]> {
  const url = workflowId
    ? `${BASE}/executions?workflow_id=${workflowId}`
    : `${BASE}/executions`;
  const res = await fetch(url);
  return res.json();
}

export async function getExecution(id: string): Promise<Execution> {
  const res = await fetch(`${BASE}/executions/${id}`);
  return res.json();
}

export async function executeWorkflow(id: string): Promise<{ execution_id: string }> {
  const res = await fetch(`${BASE}/workflows/${id}/execute`, { method: "POST" });
  return res.json();
}

export async function cancelExecution(id: string): Promise<{ cancelled: boolean }> {
  const res = await fetch(`${BASE}/executions/${id}/cancel`, { method: "POST" });
  return res.json();
}

export function connectWebSocket(onStats: (s: Stats) => void): WebSocket {
  const ws = new WebSocket(
    `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/ws`
  );
  ws.onmessage = (e) => onStats(JSON.parse(e.data));
  return ws;
}
