import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import {
  Dashboard,
  Homologacoes,
  Customizacoes,
  Atividades,
  Releases,
  Relatorios,
  Playbooks,
  Admin,
} from './pages';

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
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/homologacao" element={<Homologacoes />} />
            <Route path="/customizacao" element={<Customizacoes />} />
            <Route path="/atividade" element={<Atividades />} />
            <Route path="/release" element={<Releases />} />
            <Route path="/relatorios" element={<Relatorios />} />
            <Route path="/playbooks" element={<Playbooks />} />
            <Route path="/admin" element={<Admin />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
