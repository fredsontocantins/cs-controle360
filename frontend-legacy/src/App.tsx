import { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ErrorBoundary } from './components/ErrorBoundary';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import { RequireAuth } from './components/RequireAuth';

const Login = lazy(() => import('./pages/Login').then((module) => ({ default: module.Login })));
const Dashboard = lazy(() => import('./pages/Dashboard').then((module) => ({ default: module.Dashboard })));
const Homologacoes = lazy(() => import('./pages/Homologacoes').then((module) => ({ default: module.Homologacoes })));
const Customizacoes = lazy(() => import('./pages/Customizacoes').then((module) => ({ default: module.Customizacoes })));
const Atividades = lazy(() => import('./pages/Atividades').then((module) => ({ default: module.Atividades })));
const Releases = lazy(() => import('./pages/Releases').then((module) => ({ default: module.Releases })));
const Relatorios = lazy(() => import('./pages/Relatorios').then((module) => ({ default: module.Relatorios })));
const Playbooks = lazy(() => import('./pages/Playbooks').then((module) => ({ default: module.Playbooks })));
const AnaliseExecutiva = lazy(() => import('./pages/AnaliseExecutiva').then((module) => ({ default: module.AnaliseExecutiva })));
const Admin = lazy(() => import('./pages/Admin').then((module) => ({ default: module.Admin })));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60,
      retry: 1,
    },
  },
});

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Suspense
            fallback={
              <div className="flex min-h-screen items-center justify-center bg-gray-50">
                <div className="text-sm font-medium text-gray-600">Carregando módulos...</div>
              </div>
            }
          >
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/*" element={<ProtectedApp />} />
            </Routes>
          </Suspense>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

function ProtectedApp() {
  return (
    <RequireAuth>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/homologacao" element={<Homologacoes />} />
          <Route path="/customizacao" element={<Customizacoes />} />
          <Route path="/atividade" element={<Atividades />} />
          <Route path="/release" element={<Releases />} />
          <Route path="/relatorios" element={<Relatorios />} />
          <Route path="/playbooks" element={<Playbooks />} />
          <Route path="/analise-executiva" element={<AnaliseExecutiva />} />
          <Route
            path="/admin"
            element={
              <RequireAuth adminOnly>
                <Admin />
              </RequireAuth>
            }
          />
        </Routes>
      </Layout>
    </RequireAuth>
  );
}

export default App;
