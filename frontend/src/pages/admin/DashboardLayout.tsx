import { useState } from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';

const NAV_ITEMS = [
  { to: '/admin/metrics', label: '数据看板' },
  { to: '/admin/knowledge', label: '知识库管理' },
  { to: '/admin/hitl', label: '人工介入' },
  { to: '/admin/config', label: '配置中心' },
  { to: '/admin/sandbox', label: '沙盒测试' },
] as const;

export default function DashboardLayout() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-30 w-60 bg-white border-r border-gray-200
          transform transition-transform duration-200 ease-in-out
          lg:translate-x-0 lg:static lg:z-auto
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <div className="flex items-center justify-between h-14 px-4 border-b border-gray-200">
          <span className="text-lg font-semibold text-gray-800">Cuckoo-Echo</span>
          <button
            className="lg:hidden p-1 text-gray-500 hover:text-gray-700"
            onClick={() => setSidebarOpen(false)}
            aria-label="关闭侧边栏"
          >
            ✕
          </button>
        </div>

        <nav aria-label="管理后台导航" className="mt-2 px-2 space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Main area */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* Top bar */}
        <header className="flex items-center justify-between h-14 px-4 bg-white border-b border-gray-200 shrink-0">
          <button
            className="lg:hidden p-1.5 text-gray-500 hover:text-gray-700"
            onClick={() => setSidebarOpen(true)}
            aria-label="打开侧边栏"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          <div className="flex items-center gap-4 ml-auto">
            {user && (
              <span className="text-sm text-gray-600">
                {user.email}
                {user.tenantName && (
                  <span className="ml-2 text-gray-400">({user.tenantName})</span>
                )}
              </span>
            )}
            <button
              onClick={logout}
              className="px-3 py-1.5 text-sm text-gray-600 hover:text-red-600 border border-gray-300 rounded-md hover:border-red-300 transition-colors"
            >
              退出登录
            </button>
          </div>
        </header>

        {/* Child route content */}
        <main className="flex-1 overflow-auto p-4">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
