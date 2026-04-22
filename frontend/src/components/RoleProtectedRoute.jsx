import { Navigate } from "react-router-dom";
import { hasRequiredRole } from "../services/roleService";
import { getStoredUser } from "../services/sessionService";

function RoleProtectedRoute({ children, allowedRoles }) {
  const user = getStoredUser();

  if (!user) {
    return <Navigate to="/" replace />;
  }

  if (!hasRequiredRole(user.role, allowedRoles)) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

export default RoleProtectedRoute;
