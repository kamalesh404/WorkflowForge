import { BrowserRouter, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Executions from "./pages/Executions";
import ExecutionDetail from "./pages/ExecutionDetail";
import WorkflowDetail from "./pages/WorkflowDetail";
import Workflows from "./pages/Workflows";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="workflows" element={<Workflows />} />
          <Route path="workflows/:id" element={<WorkflowDetail />} />
          <Route path="executions" element={<Executions />} />
          <Route path="executions/:id" element={<ExecutionDetail />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
