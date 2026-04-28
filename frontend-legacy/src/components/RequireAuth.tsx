import { Navigate, useLocation } from 'react-router-dom';
import type { ReactNode } from 'react';
import { clearAuthSession, getAuthToken, getAuthUser, isAuthSessionExpired } from '../services/api';

export function RequireAuth({ children, adminOnly = false }: { children: ReactNode; adminOnly?: boolean }) {
  const location = useLocation();
  const token = getAuthToken();
  const user = getAuthUser();

  if (!token || !user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (isAuthSessionExpired()) {
    clearAuthSession();
    return <Navigate to="/login" replace state={{ from: location, sessionExpired: true }} />;
  }

  if (adminOnly && user.role !== 'admin') {
    return <Navigate to="/" replace />;
  }

  return children;
}
