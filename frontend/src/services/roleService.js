export function hasRequiredRole(userRoles, allowedRoles) {
    return allowedRoles.includes(userRoles);
}