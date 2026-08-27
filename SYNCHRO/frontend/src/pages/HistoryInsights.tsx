import { useApp } from '../context/AppContext';
import { cn } from '../utils/cn';
import { 
  TrendingUp, 
  TrendingDown, 
  Target, 
  Clock, 
  Award, 
  AlertTriangle,
  Filter,
  Download
} from 'lucide-react';
import { useState } from 'react';

export function HistoryInsights() {
  const { trades } = useApp();
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d' | 'all'>('30d');

  const closedTrades = trades.filter(t => t.status === 'closed');
  const filteredTrades = timeRange === 'all' 
    ? closedTrades 
    : closedTrades.filter(t => {
        const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90;
        const cutoff = new Date(Date.now() - days * 24 * 60 * 60 * 1000);
        return new Date(t.closedAt || t.openedAt) >= cutoff;
      });

  const wins = filteredTrades.filter(t => (t.pnl || 0) > 0);
  const losses = filteredTrades.filter(t => (t.pnl || 0) < 0);
  const totalPnl = filteredTrades.reduce((sum, t) => sum + (t.pnl || 0), 0);
  const winRate = filteredTrades.length > 0 ? (wins.length / filteredTrades.length) * 100 : 0;
  const avgWin = wins.length > 0 ? wins.reduce((sum, t) => sum + (t.pnl || 0), 0) / wins.length : 0;
  const avgLoss = losses.length > 0 ? losses.reduce((sum, t) => sum + Math.abs(t.pnl || 0), 0) / losses.length : 0;
  const profitFactor = losses.length > 0 && avgLoss > 0 ? (avgWin * wins.length) / (avgLoss * losses.length) : 0;

  // Best/worst analysis
  const symbolStats = filteredTrades.reduce((acc, t) => {
    if (!acc[t.symbol]) acc[t.symbol] = { wins: 0, losses: 0, totalPnl: 0, count: 0 };
    acc[t.symbol].count++;
    acc[t.symbol].totalPnl += t.pnl || 0;
    if ((t.pnl || 0) > 0) acc[t.symbol].wins++;
    else acc[t.symbol].losses++;
    return acc;
  }, {} as Record<string, { wins: number; losses: number; totalPnl: number; count: number }>);

  const bestSymbol = Object.entries(symbolStats).sort((a, b) => b[1].totalPnl - a[1].totalPnl)[0];
  const worstSymbol = Object.entries(symbolStats).sort((a, b) => a[1].totalPnl - b[1].totalPnl)[0];

  // Hour analysis (simplified)
  const hourStats = filteredTrades.reduce((acc, t) => {
    const hour = new Date(t.openedAt).getHours();
    if (!acc[hour]) acc[hour] = { wins: 0, losses: 0 };
    if ((t.pnl || 0) > 0) acc[hour].wins++;
    else acc[hour].losses++;
    return acc;
  }, {} as Record<number, { wins: number; losses: number }>);

  const bestHour = Object.entries(hourStats).sort((a, b) => {
    const wrA = a[1].wins / (a[1].wins + a[1].losses);
    const wrB = b[1].wins / (b[1].wins + b[1].losses);
    return wrB - wrA;
  })[0];

  const insights = [
    {
      type: 'best_hour',
      title: 'Best Trading Hour',
      description: bestHour ? `${parseInt(bestHour[0])}:00-${parseInt(bestHour[0])+1}:00 UTC` : 'N/A',
      value: bestHour ? `${((bestHour[1].wins / (bestHour[1].wins + bestHour[1].losses)) * 100).toFixed(0)}% WR` : 'N/A',
      icon: Clock,
      color: 'text-green-600',
    },
    {
      type: 'best_symbol',
      title: 'Best Symbol',
      description: bestSymbol?.[0] || 'N/A',
      value: bestSymbol ? `${bestSymbol[1].wins}/${bestSymbol[1].count} (${((bestSymbol[1].wins / bestSymbol[1].count) * 100).toFixed(0)}% WR)` : 'N/A',
      icon: Award,
      color: 'text-blue-600',
    },
    {
      type: 'worst_symbol',
      title: 'Worst Symbol',
      description: worstSymbol?.[0] || 'N/A',
      value: worstSymbol ? `${worstSymbol[1].losses}/${worstSymbol[1].count} losses` : 'N/A',
      icon: AlertTriangle,
      color: 'text-red-600',
    },
    {
      type: 'risk',
      title: 'Risk Metric',
      description: 'Avg Win / Avg Loss',
      value: avgLoss > 0 ? `${(avgWin / avgLoss).toFixed(2)}:1` : 'N/A',
      icon: Target,
      color: 'text-amber-600',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-synchro-text-primary">History & Insights</h1>
          <p className="text-synchro-text-secondary">Auto-generated insights from your trading history</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex bg-synchro-border rounded-xl p-1" role="group">
            {(['7d', '30d', '90d', 'all'] as const).map(range => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={cn(
                  'px-3 py-1.5 text-sm font-medium rounded-lg transition-all',
                  timeRange === range 
                    ? 'bg-synchro-navy text-white' 
                    : 'text-synchro-text-secondary hover:text-synchro-text-primary'
                )}
              >
                {range === '7d' ? '7D' : range === '30d' ? '30D' : range === '90d' ? '90D' : 'All'}
              </button>
            ))}
          </div>
          <button className="synchro-btn-secondary px-4 py-2">
            <Download className="w-4 h-4 mr-2" /> Export
          </button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
        <MetricCard label="Total Trades" value={filteredTrades.length} icon={<Filter className="w-5 h-5" />} />
        <MetricCard label="Win Rate" value={`${winRate.toFixed(1)}%`} icon={<TrendingUp className="w-5 h-5" />} color="green" />
        <MetricCard label="Profit Factor" value={profitFactor.toFixed(2)} icon={<Target className="w-5 h-5" />} color="amber" />
        <MetricCard label="Avg Win" value={`$${avgWin.toFixed(2)}`} icon={<TrendingUp className="w-5 h-5" />} color="green" />
        <MetricCard label="Avg Loss" value={`$${avgLoss.toFixed(2)}`} icon={<TrendingDown className="w-5 h-5" />} color="red" />
        <MetricCard label="Net P&L" value={`${totalPnl >= 0 ? '+' : ''}$${totalPnl.toFixed(2)}`} icon={<TrendingUp className="w-5 h-5" />} color={totalPnl >= 0 ? 'green' : 'red'} />
      </div>

      {/* Insights Cards */}
      <section>
        <h2 className="text-lg font-semibold text-synchro-text-primary mb-4">Auto Insights</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {insights.map((insight) => (
            <InsightCard key={insight.type} {...insight} />
          ))}
        </div>
      </section>

      {/* Symbol Performance Table */}
      <section className="synchro-card">
        <div className="p-4 border-b border-synchro-border flex items-center justify-between">
          <h3 className="text-lg font-semibold text-synchro-text-primary">Symbol Performance</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-synchro-border">
                <th className="text-left p-3 text-xs font-medium text-synchro-text-secondary uppercase tracking-wider">Symbol</th>
                <th className="text-right p-3 text-xs font-medium text-synchro-text-secondary uppercase tracking-wider">Trades</th>
                <th className="text-right p-3 text-xs font-medium text-synchro-text-secondary uppercase tracking-wider">Win Rate</th>
                <th className="text-right p-3 text-xs font-medium text-synchro-text-secondary uppercase tracking-wider">Total P&L</th>
                <th className="text-right p-3 text-xs font-medium text-synchro-text-secondary uppercase tracking-wider">Avg P&L</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(symbolStats)
                .sort((a, b) => b[1].totalPnl - a[1].totalPnl)
                .map(([symbol, stats]) => (
                  <tr key={symbol} className="border-b border-synchro-border/50 hover:bg-synchro-border/50">
                    <td className="p-3 font-medium text-synchro-text-primary">{symbol}</td>
                    <td className="text-right p-3 text-synchro-text-secondary">{stats.count}</td>
                    <td className="text-right p-3 font-medium text-green-600">
                      {stats.count > 0 ? `${((stats.wins / stats.count) * 100).toFixed(1)}%` : 'N/A'}
                    </td>
                    <td className="text-right p-3 font-medium text-synchro-text-primary">
                      ${stats.totalPnl.toFixed(2)}
                    </td>
                    <td className="text-right p-3 text-synchro-text-secondary">
                      ${(stats.totalPnl / stats.count).toFixed(2)}
                    </td>
                  </tr>
                ))}
              {Object.keys(symbolStats).length === 0 && (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-synchro-text-secondary">
                    No trading data for selected period
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Equity Curve */}
      <section className="synchro-card p-4">
        <h3 className="text-lg font-semibold text-synchro-text-primary mb-4">Equity Curve ({timeRange === 'all' ? 'All Time' : timeRange.toUpperCase()})</h3>
        <div className="h-64 bg-synchro-border/50 rounded-xl flex items-center justify-center">
          <p className="text-synchro-text-secondary">Equity chart would render here with recharts</p>
        </div>
      </section>
    </div>
  );
}

function MetricCard({ label, value, icon, color }: { label: string; value: string | number; icon?: React.ReactNode; color?: 'blue' | 'green' | 'red' | 'amber' }) {
  const colorMap = {
    blue: 'text-blue-600',
    green: 'text-green-600',
    red: 'text-red-600',
    amber: 'text-amber-600',
  };
  return (
    <div className="synchro-card p-4">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-synchro-text-secondary uppercase tracking-wider">{label}</p>
        {icon && <div className={cn('text-synchro-text-secondary', color && colorMap[color])}>{icon}</div>}
      </div>
      <p className={cn('text-2xl font-bold text-synchro-text-primary mt-2', color && colorMap[color])}>{value}</p>
    </div>
  );
}

function InsightCard({ 
  title, 
  description, 
  value, 
  icon: Icon, 
  color 
}: { 
  title: string; 
  description: string; 
  value: string; 
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}) {
  return (
    <div className="synchro-card p-4">
      <div className="flex items-start justify-between mb-3">
        <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center', `${color} bg-opacity-10`)}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      <p className="text-sm font-medium text-synchro-text-primary mb-1">{title}</p>
      <p className="text-2xl font-bold text-synchro-text-primary mb-1">{value}</p>
      <p className="text-xs text-synchro-text-secondary">{description}</p>
    </div>
  );
}