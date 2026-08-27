import { useState } from 'react';
import { Outlet, NavLink, useLocation } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { 
  LayoutDashboard, 
  CandlestickChart, 
  FileText, 
  History, 
  CheckCircle2, 
  Settings, 
  FileBarChart,
  Zap,
  Shield,
  HelpCircle,
  Menu,
  X,
  ChevronDown
} from 'lucide-react';
import { cn } from '../utils/cn';

const navigation = [
  { path: '/dashboard', label: 'Command', icon: LayoutDashboard, description: 'Overview & control' },
  { path: '/charts', label: 'Charts', icon: CandlestickChart, description: 'Live market view' },
  { path: '/trades', label: 'Trades', icon: FileText, description: 'Open & recent trades' },
  { path: '/history', label: 'History', icon: History, description: 'Insights & analytics' },
  { path: '/approvals', label: 'Approvals', icon: CheckCircle2, description: 'Pending decisions' },
  { path: '/reports', label: 'Reports', icon: FileBarChart, description: 'Weekly & exports' },
  { path: '/settings', label: 'Settings', icon: Settings, description: 'Capital & markets' },
];

export function Layout() {
  const { user, killSwitchActive, activeAccount, explainMode, setExplainMode, setKillSwitch } = useApp();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="min-h-screen bg-synchro-bg">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside 
        className={cn(
          'fixed lg:static inset-y-0 left-0 z-50 w-64 bg-white border-r border-synchro-border transform transition-transform duration-300',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
        aria-label="Main navigation"
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="p-5 border-b border-synchro-border flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-synchro-navy flex items-center justify-center">
                <Zap className="w-6 h-6 text-white" />
              </div>
              <span className="font-bold text-xl text-synchro-text-primary">SYNCHRO</span>
            </div>
            <button 
              className="lg:hidden p-2 rounded-lg hover:bg-synchro-border"
              onClick={() => setSidebarOpen(false)}
              aria-label="Close sidebar"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Account status */}
          <div className="p-4 border-b border-synchro-border">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-medium text-synchro-text-secondary uppercase tracking-wider">
                Active Account
              </span>
              {activeAccount?.isDemo && (
                <span className="synchro-badge synchro-badge-info">Demo</span>
              )}
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-synchro-text-secondary">{activeAccount?.name}</span>
              <span className="font-semibold text-synchro-text-primary">
                ${activeAccount?.allocatedCapital?.toLocaleString() || 0}
              </span>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1" aria-label="Main navigation">
            {navigation.map((item) => {
              const active = isActive(item.path);
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={cn(
                    'flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-medium transition-all duration-200',
                    active
                      ? 'bg-synchro-card text-synchro-text-primary shadow-sm'
                      : 'text-synchro-text-secondary hover:bg-synchro-border hover:text-synchro-text-primary'
                  )}
                  title={item.description}
                  onClick={() => setSidebarOpen(false)}
                >
                  <item.icon className={cn('w-5 h-5 flex-shrink-0', active && 'text-synchro-navy')} />
                  <span className="truncate">{item.label}</span>
                </NavLink>
              );
            })}
          </nav>

          {/* Bottom section */}
          <div className="p-4 border-t border-synchro-border space-y-2">
            {/* Kill Switch */}
            <button
              onClick={() => setKillSwitch(!killSwitchActive)}
              className={cn(
                'w-full flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-medium transition-all duration-200',
                killSwitchActive
                  ? 'bg-red-50 text-red-700 border border-red-200'
                  : 'bg-synchro-border text-synchro-text-secondary hover:bg-synchro-card hover:text-synchro-text-primary'
              )}
              aria-pressed={killSwitchActive}
            >
              <Shield className={cn('w-5 h-5 flex-shrink-0', killSwitchActive && 'text-red-600')} />
              <span>{killSwitchActive ? 'KILL SWITCH ACTIVE' : 'Activate Kill Switch'}</span>
            </button>

            {/* Explain Mode Toggle */}
            <label className="w-full flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-medium transition-all duration-200 cursor-pointer hover:bg-synchro-border">
              <HelpCircle className="w-5 h-5 flex-shrink-0 text-synchro-text-secondary" />
              <span>Explain Mode</span>
              <input
                type="checkbox"
                checked={explainMode}
                onChange={(e) => setExplainMode(e.target.checked)}
                className="w-5 h-5 rounded border-synchro-border text-synchro-navy focus:ring-synchro-navy"
              />
            </label>

            {/* User Menu */}
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="w-full flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-medium text-synchro-text-secondary hover:bg-synchro-border hover:text-synchro-text-primary transition-all duration-200"
              >
                <div className="w-8 h-8 rounded-full bg-synchro-card flex items-center justify-center">
                  <span className="text-synchro-text-primary font-semibold text-sm">
                    {user?.name?.charAt(0) || 'U'}
                  </span>
                </div>
                <span className="flex-1 text-left truncate">{user?.name}</span>
                <ChevronDown className="w-4 h-4" />
              </button>

              {showUserMenu && (
                <div className="absolute bottom-full left-0 right-0 mb-2 bg-white rounded-xl border border-synchro-border shadow-lg py-2 animate-scale-in">
                  <div className="px-4 py-2 border-b border-synchro-border">
                    <p className="text-xs text-synchro-text-secondary">{user?.email}</p>
                    <p className="text-xs text-synchro-text-secondary">{activeAccount?.isDemo ? 'Demo Mode' : 'Live Mode'}</p>
                  </div>
                  <NavLink
                    to="/settings"
                    className="block px-4 py-2 text-sm text-synchro-text-secondary hover:bg-synchro-border hover:text-synchro-text-primary"
                    onClick={() => setShowUserMenu(false)}
                  >
                    Settings
                  </NavLink>
                  <button className="w-full text-left px-4 py-2 text-sm text-synchro-text-secondary hover:bg-synchro-border hover:text-synchro-text-primary">
                    Sign out
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </aside>

      {/* Mobile menu button */}
      <button
        className="lg:hidden fixed top-4 left-4 z-50 p-2 rounded-xl bg-white border border-synchro-border shadow-lg"
        onClick={() => setSidebarOpen(true)}
        aria-label="Open menu"
      >
        <Menu className="w-6 h-6 text-synchro-text-primary" />
      </button>

      {/* Main content */}
      <main className="lg:ml-64 min-h-screen">
        {/* Top bar */}
        <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-sm border-b border-synchro-border">
          <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
            <h1 className="text-xl font-bold text-synchro-text-primary">
              {navigation.find(n => isActive(n.path))?.label || 'SYNCHRO'}
            </h1>
            <div className="flex items-center gap-3">
              {/* Demo replay link */}
              <a 
                href="/demo" 
                className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium text-synchro-gold hover:bg-amber-50 transition-colors"
              >
                <Zap className="w-4 h-4" />
                Demo Replay
              </a>
            </div>
          </div>
        </header>

        {/* Page content */}
        <div className="max-w-7xl mx-auto p-4 lg:p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}