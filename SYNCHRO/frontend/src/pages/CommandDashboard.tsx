import { useApp } from '../context/AppContext';
import { 
  TrendingUp, 
  DollarSign, 
  Shield, 
  Target,
  FileText
} from 'lucide-react';
import { cn } from '../utils/cn';
import { EquityChart } from '../components/EquityChart';
import { PhaseJourney } from '../components/PhaseJourney';
import { OpenTradesList } from '../components/OpenTradesList';
import { MarketStatusCards } from '../components/MarketStatusCards';

export function CommandDashboard() {
  const { 
    activeAccount, 
    trades, 
    equityHistory, 
    marketData, 
    killSwitchActive, 
    setKillSwitch,
    user 
  } = useApp();

  const openTrades = trades.filter(t => t.status !== 'closed');
  const todayTrades = trades.filter(t => {
    const today = new Date().toDateString();
    return new Date(t.openedAt).toDateString() === today;
  });
  const todayPnl = todayTrades.reduce((sum, t) => sum + (t.pnl || 0), 0);
  const totalEquity = activeAccount?.allocatedCapital || 0;
  const currentEquity = equityHistory[0]?.equity || totalEquity;
  const totalReturn = totalEquity > 0 ? ((currentEquity - totalEquity) / totalEquity) * 100 : 0;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Hero Section */}
      <section className="synchro-card-elevated p-6 lg:p-8">
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Main Status */}
          <div className="lg:col-span-2 space-y-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h1 className="text-3xl lg:text-4xl font-bold text-synchro-text-primary">
                  Welcome back, {user?.name?.split(' ')[0] || 'Trader'}
                </h1>
                <p className="text-synchro-text-secondary mt-1">
                  {activeAccount?.isDemo ? 'Demo Mode' : 'Live Trading'} • 
                  {activeAccount?.name} • 
                  ${activeAccount?.allocatedCapital?.toLocaleString() || 0}
                </p>
              </div>
              <div className="flex items-center gap-3 flex-shrink-0">
                {/* Status Pulse */}
                <div className="relative">
                  <div className={cn(
                    'w-3 h-3 rounded-full',
                    killSwitchActive ? 'bg-red-500' : 'bg-green-500 animate-pulse-slow'
                  )} />
                  <span className="absolute -top-2 -right-2 w-1.5 h-1.5 rounded-full bg-green-500" />
                </div>
                <span className={cn(
                  'text-sm font-medium',
                  killSwitchActive ? 'text-red-600' : 'text-green-600'
                )}>
                  {killSwitchActive ? 'HALTED' : 'SYNCHRO is watching 👁'}
                </span>
              </div>
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricCard
                label="Current Equity"
                value={`$${currentEquity.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`}
                change={totalReturn}
                icon={<DollarSign className="w-5 h-5" />}
              />
              <MetricCard
                label="Today's P&L"
                value={`$${todayPnl.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`}
                change={todayPnl}
                icon={<TrendingUp className="w-5 h-5" />}
              />
              <MetricCard
                label="Total Return"
                value={`${totalReturn >= 0 ? '+' : ''}${totalReturn.toFixed(2)}%`}
                icon={<Target className="w-5 h-5" />}
              />
              <MetricCard
                label="Open Trades"
                value={openTrades.length.toString()}
                icon={<FileText className="w-5 h-5" />}
              />
            </div>

            {/* Equity Chart */}
            <div className="synchro-card p-4">
              <h3 className="text-lg font-semibold text-synchro-text-primary mb-4">Equity Curve</h3>
              <EquityChart data={equityHistory} initialCapital={totalEquity} />
            </div>
          </div>

          {/* Side Panel */}
          <div className="space-y-4">
            {/* Kill Switch */}
            <div className="synchro-card p-4">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-red-50 flex items-center justify-center">
                    <Shield className="w-5 h-5 text-red-600" />
                  </div>
                  <div>
                    <p className="font-semibold text-synchro-text-primary">Kill Switch</p>
                    <p className="text-xs text-synchro-text-secondary">Emergency halt all trading</p>
                  </div>
                </div>
                <button
                  onClick={() => setKillSwitch(!killSwitchActive)}
                  className={cn(
                    'w-12 h-7 rounded-full flex items-center justify-center transition-all duration-300 relative',
                    killSwitchActive ? 'bg-red-600' : 'bg-synchro-border'
                  )}
                  aria-label={killSwitchActive ? 'Deactivate kill switch' : 'Activate kill switch'}
                >
                  <div className={cn(
                    'w-5 h-5 rounded-full bg-white shadow transition-transform duration-300',
                    killSwitchActive ? 'translate-x-full' : 'translate-x-0'
                  )} />
                </button>
              </div>
              {killSwitchActive && (
                <div className="p-3 bg-red-50 rounded-lg border border-red-200 text-sm text-red-700">
                  ⚠️ All trading halted. No new positions will be opened.
                </div>
              )}
            </div>

            {/* Phase Journey */}
            <PhaseJourney currentPhase={2} />
          </div>
        </div>
      </section>

      {/* Market Status Cards */}
      <MarketStatusCards data={marketData} />

      {/* Open Trades */}
      <OpenTradesList trades={openTrades} />
    </div>
  );
}

function MetricCard({ label, value, change, icon }: { 
  label: string; 
  value: string; 
  change?: number; 
  icon: React.ReactNode 
}) {
  const isPositive = (change ?? 0) >= 0;
  
  return (
    <div className="synchro-card p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-synchro-text-secondary uppercase tracking-wider">
            {label}
          </p>
          <p className="text-2xl font-bold text-synchro-text-primary mt-1">{value}</p>
        </div>
        <div className="w-10 h-10 rounded-xl bg-synchro-card flex items-center justify-center text-synchro-text-primary">
          {icon}
        </div>
      </div>
      {change !== undefined && (
        <p className={cn(
          'mt-2 text-sm font-medium',
          isPositive ? 'text-green-600' : 'text-red-600'
        )}>
          {isPositive ? '+' : ''}{change.toFixed(2)}%
        </p>
      )}
    </div>
  );
}