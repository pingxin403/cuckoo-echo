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
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack);
  }

  handleRefresh = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div
          role="alert"
          aria-label="页面错误"
          className="flex min-h-[200px] flex-col items-center justify-center gap-4 rounded-lg bg-gray-50 p-8 text-center"
        >
          <p className="text-lg font-medium text-gray-800">页面出现错误</p>
          <p className="text-sm text-gray-500">
            {this.state.error?.message ?? '未知错误'}
          </p>
          <button
            onClick={this.handleRefresh}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
            aria-label="刷新页面"
          >
            刷新页面
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
