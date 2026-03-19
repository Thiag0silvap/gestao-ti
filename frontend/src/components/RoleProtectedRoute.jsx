import { Navigate } from "react-router-dom";
import { hasRequiredRole } from "../services/roleService";

function RoleProtectedRoute({ children, allowedRoles }) {
  const userRaw = localStorage.getItem("user");

  if (!userRaw) {
    return <Navigate to="/" replace />;
  }

  const user = JSON.parse(userRaw);

  if (!hasRequiredRole(user.role, allowedRoles)) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

export default RoleProtectedRoute;