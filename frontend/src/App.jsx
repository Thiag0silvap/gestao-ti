import { BrowserRouter, Routes, Route } from "react-router-dom";

import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Computers from "./pages/Computers";
import Alerts from "./pages/Alerts";
import Assets from "./pages/Assets";
import ComputerDetail from "./pages/ComputerDetail";
import Users from "./pages/Users";

import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import RoleProtectedRoute from "./components/RoleProtectedRoute";
import Tickets from "./pages/Tickets";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />

        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <RoleProtectedRoute allowedRoles={["admin", "technician", "operator"]}>
                <Layout>
                  <Dashboard />
                </Layout>
              </RoleProtectedRoute>
            </ProtectedRoute>
          }
        />

        <Route
          path="/alerts"
          element={
            <ProtectedRoute>
              <RoleProtectedRoute allowedRoles={["admin", "technician"]}>
                <Layout>
                  <Alerts />
                </Layout>
              </RoleProtectedRoute>
            </ProtectedRoute>
          }
        />

        <Route
          path="/computers"
          element={
            <ProtectedRoute>
              <RoleProtectedRoute allowedRoles={["admin", "technician"]}>
                <Layout>
                  <Computers />
                </Layout>
              </RoleProtectedRoute>
            </ProtectedRoute>
          }
        />

        <Route
          path="/computers/:id"
          element={
            <ProtectedRoute>
              <RoleProtectedRoute allowedRoles={["admin", "technician"]}>
                <Layout>
                  <ComputerDetail />
                </Layout>
              </RoleProtectedRoute>
            </ProtectedRoute>
          }
        />

        <Route
          path="/assets"
          element={
            <ProtectedRoute>
              <RoleProtectedRoute allowedRoles={["admin", "technician"]}>
                <Layout>
                  <Assets />
                </Layout>
              </RoleProtectedRoute>
            </ProtectedRoute>
          }
        />

        <Route
          path="/users"
          element={
            <ProtectedRoute>
              <RoleProtectedRoute allowedRoles={["admin"]}>
                <Layout>
                  <Users />
                </Layout>
              </RoleProtectedRoute>
            </ProtectedRoute>
          }
        />

        <Route
          path="/tickets"
          element={
            <ProtectedRoute>
              <RoleProtectedRoute allowedRoles={["admin", "technician", "operator"]}>
                <Layout>
                  <Tickets />
                </Layout>
              </RoleProtectedRoute>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
