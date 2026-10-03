import type { ReactNode } from "react";
import { useAuth } from "./AuthContext";
import type { Permission } from "./types";

type ProtectedRouteProps = {
  children: ReactNode;
  fallback?: ReactNode;
  permission?: Permission;
};

export function ProtectedRoute({
  children,
  fallback = null,
  permission
}: ProtectedRouteProps) {
  const auth = useAuth();

  if (auth.session.isGuest) {
    return <>{fallback}</>;
  }

  if (permission && !auth.can(permission)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}
