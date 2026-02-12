import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import RequireAuth from "./auth/RequireAuth";

// Pages
import Dashboard from "./pages/Dashboard";
import Traces from "./pages/Traces";
import Evaluators from "./pages/Evaluators";
import Sessions from "./pages/Sessions";
import Alerts from "./pages/Alerts";
import Datasets from "./pages/Datasets";
import Annotations from "./pages/Annotations";
import Audit from "./pages/Audit";
import Settings from "./pages/Settings";
import Prompts from "./pages/Prompts";
import CreatePrompt from "./pages/CreatePrompt";
import CreateTemplate from "./pages/CreateTemplate";
import CreateEvaluator from "./pages/CreateEvaluator";
import LoginPage from "./pages/LoginPage";

// Layout
import Sidebar from "./components/Sidebar";
import Navbar from "./components/NavBar";

export default function App() {
  return (
    <Router>
      <Routes>
        {/* Public Login Page */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected Routes */}
        <Route
          path="/*"
          element={
            <RequireAuth>
              <ProtectedLayout />
            </RequireAuth>
          }
        />

        {/* Default → redirect to login */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </Router>
  );
}

function ProtectedLayout() {
  return (
    <div className="flex h-screen bg-[#0e1117] text-[#e0e0e0] overflow-hidden">
      {/* Left Sidebar */}
      <Sidebar />

      {/* Right side → Navbar + Dynamic Page Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        
        {/* Top Navbar */}
        <Navbar />

        {/* Page container */}
        <main className="flex-1 overflow-y-auto p-8">
          <div className="max-w-[1400px] mx-auto">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="traces" element={<Traces />} />
              <Route path="sessions" element={<Sessions />} />
              <Route path="evaluators" element={<Evaluators />} />
              <Route path="evaluators/new" element={<CreateEvaluator />} />
              <Route path="templates/new" element={<CreateTemplate />} />
              <Route path="annotations" element={<Annotations />} />
              <Route path="prompts" element={<Prompts />} />
              <Route path="prompts/new" element={<CreatePrompt />} />
              <Route path="alerts" element={<Alerts />} />
              <Route path="datasets" element={<Datasets />} />
              <Route path="audit" element={<Audit />} />
              <Route path="settings" element={<Settings />} />

              {/* Default inside protected layout */}
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </div>
        </main>
      </div>
    </div>
  );
}
