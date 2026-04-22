import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  clearAuthSession,
  getAuthSessionExpiresAt,
  getAuthSessionRemainingMs,
  getAuthUser,
} from '../services/api';

const navItems = [
  { path: '/', label: 'Dashboard', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
  { path: '/homologacao', label: 'Homologações', icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z' },
  { path: '/customizacao', label: 'Customizações', icon: 'M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4' },
  { path: '/atividade', label: 'Atividades', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01' },
  { path: '/release', label: 'Releases', icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z' },
  { path: '/relatorios', label: 'Relatórios', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
  { path: '/playbooks', label: 'Playbooks', icon: 'M12 20h9' },
  { path: '/admin', label: 'Admin', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z' },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const user = getAuthUser();
  const [remainingMs, setRemainingMs] = useState<number | null>(() => getAuthSessionRemainingMs());
  const visibleNavItems = user?.role === 'admin' ? navItems : navItems.filter((item) => item.path !== '/admin');
  const expiresAt = useMemo(() => getAuthSessionExpiresAt(), []);

  useEffect(() => {
    const tick = () => {
      const remaining = getAuthSessionRemainingMs();
      setRemainingMs(remaining);
      if (remaining !== null && remaining <= 0) {
        clearAuthSession();
        navigate('/login', { replace: true, state: { sessionExpired: true } });
      }
    };

    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, [navigate]);

  const handleLogout = () => {
    clearAuthSession();
    setRemainingMs(null);
    navigate('/login', { replace: true });
  };

  const formatRemaining = (value: number | null) => {
    if (value === null) {
      return 'Sessão ativa';
    }
    const totalSeconds = Math.max(0, Math.floor(value / 1000));
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    if (hours > 0) {
      return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  };

  const sessionTone =
    remainingMs === null
      ? 'bg-white/10 text-white/80'
      : remainingMs <= 2 * 60 * 1000
        ? 'bg-red-500/20 text-red-100 ring-1 ring-red-300/30'
        : remainingMs <= 10 * 60 * 1000
          ? 'bg-amber-400/20 text-amber-100 ring-1 ring-amber-200/30'
          : 'bg-emerald-400/20 text-emerald-100 ring-1 ring-emerald-200/30';

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-[#0d3b66] text-white">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-8">
              <Link to="/" className="flex items-center gap-2">
                <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                <span className="font-bold text-lg">CS Controle 360</span>
              </Link>
              <div className="hidden md:flex gap-1">
                {visibleNavItems.map((item) => {
                  const isActive = location.pathname === item.path;
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-white/20 text-white'
                          : 'text-white/80 hover:bg-white/10 hover:text-white'
                      }`}
                    >
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={item.icon} />
                      </svg>
                      {item.label}
                    </Link>
                  );
                })}
              </div>
            </div>
            <div className="flex items-center gap-3">
              {expiresAt && (
                <div className={`hidden lg:flex flex-col items-end rounded-full px-3 py-1.5 text-[11px] font-medium ${sessionTone}`}>
                  <span>Sessão expira em {formatRemaining(remainingMs)}</span>
                  <span className="opacity-70">{expiresAt}</span>
                </div>
              )}
              {user && (
                <div className="hidden sm:flex flex-col items-end">
                  <span className="text-sm font-medium">{user.full_name || user.username}</span>
                  <span className="text-[11px] uppercase tracking-wider text-white/70">
                    {user.role} · {user.provider}
                  </span>
                </div>
              )}
              <button
                type="button"
                onClick={handleLogout}
                className="rounded-lg border border-white/20 px-3 py-2 text-sm font-medium text-white/90 hover:bg-white/10"
              >
                Sair
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto">
        {children}
      </main>
    </div>
  );
}
