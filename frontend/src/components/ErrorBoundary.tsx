import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 p-4 text-center">
            <h1 className="mb-4 text-2xl font-bold text-gray-900">Algo deu errado.</h1>
            <p className="mb-6 text-gray-600">
              Desculpe pelo transtorno. Ocorreu um erro inesperado na aplicação.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
            >
              Recarregar página
            </button>
            {import.meta.env.DEV && (
              <pre className="mt-8 max-w-full overflow-auto rounded-lg bg-red-50 p-4 text-left text-xs text-red-700">
                {this.state.error?.toString()}
              </pre>
            )}
          </div>
        )
      );
    }

    return this.props.children;
  }
}
