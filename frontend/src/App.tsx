import { BrowserRouter, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Executions from "./pages/Executions";
import Workflows from "./pages/Workflows";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="workflows" element={<Workflows />} />
          <Route path="executions" element={<Executions />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
