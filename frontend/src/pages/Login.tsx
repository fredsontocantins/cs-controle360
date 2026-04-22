import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { authApi, clearAuthSession, setAuthSession } from '../services/api';
import { Badge, Button, Card, Input } from '../components';

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential: string }) => void;
          }) => void;
          renderButton: (element: HTMLElement, options: Record<string, string>) => void;
        };
      };
    };
  }
}

export function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const target = useMemo(() => (location.state as { from?: { pathname?: string } } | null)?.from?.pathname || '/', [location.state]);
  const sessionExpired = Boolean((location.state as { sessionExpired?: boolean } | null)?.sessionExpired);
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin');
  const [message, setMessage] = useState<string | null>(sessionExpired ? 'Sua sessão expirou. Entre novamente.' : null);
  const [pending, setPending] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    clearAuthSession();
    if (sessionExpired) {
      setPending(false);
      setMessage('Sua sessão expirou. Entre novamente.');
    }
  }, [sessionExpired]);

  useEffect(() => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;
    if (!clientId) {
      return;
    }

    const scriptId = 'google-identity-script';
    const existing = document.getElementById(scriptId);
    const ensureButton = () => {
      if (!window.google) return;
      const container = document.getElementById('google-button');
      if (!container) return;
      container.innerHTML = '';
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: async (response) => {
          try {
            setLoading(true);
            const result = await authApi.googleLogin({ credential: response.credential });
            if (result.status === 'pending_approval') {
              setPending(true);
              setMessage(result.message || 'Acesso Google aguardando aprovação do administrador.');
              clearAuthSession();
              return;
            }
            if (result.token) {
              setAuthSession(result.token, result.user, result.expires_at);
              navigate(target, { replace: true });
            }
          } catch (error) {
            setPending(false);
            setMessage(error instanceof Error ? error.message : 'Falha no login Google.');
            clearAuthSession();
          } finally {
            setLoading(false);
          }
        },
      });
      window.google.accounts.id.renderButton(container, {
        theme: 'outline',
        size: 'large',
        width: '320',
        text: 'signin_with',
      });
    };

    if (!existing) {
      const script = document.createElement('script');
      script.id = scriptId;
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.onload = ensureButton;
      document.head.appendChild(script);
      return;
    }

    ensureButton();
  }, [navigate, target]);

  const handleLocalLogin = async () => {
    try {
      setLoading(true);
      setMessage(null);
      const result = await authApi.login({ username, password });
      if (result.token) {
        setAuthSession(result.token, result.user, result.expires_at);
        navigate(target, { replace: true });
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Falha ao autenticar.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(13,59,102,0.16),_transparent_35%),linear-gradient(180deg,#f8fafc,#eef4fb)] px-4 py-10">
      <div className="mx-auto flex max-w-5xl flex-col gap-6 lg:flex-row lg:items-start">
        <div className="flex-1 rounded-[28px] bg-[#0d3b66] p-8 text-white shadow-2xl shadow-[#0d3b66]/20">
          <Badge variant="info">CS Controle 360</Badge>
          <h1 className="mt-5 text-4xl font-semibold leading-tight">Acesso seguro ao painel operacional e gerencial</h1>
          <p className="mt-4 max-w-xl text-sm leading-6 text-white/80">
            O acesso agora exige autenticação. O administrador inicial entra com `admin/admin` e aprova contas Google internamente antes da liberação.
          </p>
          <div className="mt-8 grid grid-cols-2 gap-3">
            <InfoCard title="Admin inicial" value="admin / admin" />
            <InfoCard title="Google" value="Aprovação interna" />
            <InfoCard title="Autorização" value="JWT assinado" />
            <InfoCard title="Sessão" value="7 dias" />
          </div>
        </div>

        <Card className="flex-1 border border-gray-200 bg-white/95 p-8 shadow-xl">
          <h2 className="text-2xl font-semibold text-gray-900">Entrar</h2>
          <p className="mt-2 text-sm text-gray-500">Use a conta local do administrador ou login Google com liberação interna.</p>

          {message && (
            <div className={`mt-4 rounded-xl border px-4 py-3 text-sm ${pending ? 'border-amber-200 bg-amber-50 text-amber-900' : 'border-red-200 bg-red-50 text-red-900'}`}>
              {message}
            </div>
          )}

          <div className="mt-6 space-y-4">
            <Input label="Usuário" value={username} onChange={(e) => setUsername(e.target.value)} />
            <Input label="Senha" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            <Button type="button" className="w-full" onClick={handleLocalLogin} disabled={loading}>
              {loading ? 'Autenticando...' : 'Entrar'}
            </Button>
          </div>

          <div className="my-6 flex items-center gap-3">
            <div className="h-px flex-1 bg-gray-200" />
            <span className="text-xs uppercase tracking-wider text-gray-400">ou</span>
            <div className="h-px flex-1 bg-gray-200" />
          </div>

          <div className="rounded-2xl border border-gray-200 bg-gray-50 p-4">
            <p className="text-sm font-medium text-gray-900">Entrar com Google</p>
            <p className="mt-1 text-xs text-gray-500">
              Se o acesso ainda não estiver liberado, você verá um status pendente até o admin aprovar.
            </p>
            <div className="mt-4" id="google-button">
              {!import.meta.env.VITE_GOOGLE_CLIENT_ID && (
                <div className="rounded-xl border border-dashed border-gray-300 bg-white px-4 py-3 text-sm text-gray-500">
                  Configure `VITE_GOOGLE_CLIENT_ID` para habilitar o botão do Google.
                </div>
              )}
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

function InfoCard({ title, value }: { title: string; value: string }) {
  return (
    <div className="rounded-2xl bg-white/10 p-4">
      <p className="text-[11px] uppercase tracking-wider text-white/60">{title}</p>
      <p className="mt-1 text-sm font-semibold text-white">{value}</p>
    </div>
  );
}
