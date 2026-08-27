import { useApp } from '../context/AppContext';
import type { Trade } from '../types';
import { cn } from '../utils/cn';
import { Filter, ChevronDown, ChevronUp, Download, RefreshCw } from 'lucide-react';
import { useState } from 'react';

export function TradeCards() {
  const { trades } = useApp();
  const [statusFilter, setStatusFilter] = useState<Trade['status'] | 'all'>('all');
  const [sortBy, setSortBy] = useState<'openedAt' | 'pnl' | 'symbol'>('openedAt');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const filteredTrades = trades
    .filter(t => statusFilter === 'all' || t.status === statusFilter)
    .sort((a, b) => {
      let aVal: any = a[sortBy];
      let bVal: any = b[sortBy];
      if (sortBy === 'openedAt') {
        aVal = new Date(aVal).getTime();
        bVal = new Date(bVal).getTime();
      }
      if (sortDir === 'asc') return aVal > bVal ? 1 : -1;
      return aVal < bVal ? 1 : -1;
    });

  const stats = {
    total: trades.length,
    open: trades.filter(t => t.status !== 'closed').length,
    won: trades.filter(t => (t.pnl || 0) > 0).length,
    lost: trades.filter(t => (t.pnl || 0) < 0).length,
    totalPnl: trades.reduce((sum, t) => sum + (t.pnl || 0), 0),
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-synchro-text-primary">Trade Cards</h1>
          <p className="text-synchro-text-secondary">Every trade with 3-bullet WHY — entry, protection, learning</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="synchro-btn-secondary px-4 py-2">
            <RefreshCw className="w-4 h-4 mr-2" /> Refresh
          </button>
          <button className="synchro-btn-secondary px-4 py-2">
            <Download className="w-4 h-4 mr-2" /> Export CSV
          </button>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard label="Total Trades" value={stats.total} icon={<Filter className="w-5 h-5" />} />
        <StatCard label="Open" value={stats.open} color="blue" />
        <StatCard label="Won" value={stats.won} color="green" />
        <StatCard label="Lost" value={stats.lost} color="red" />
        <StatCard 
          label="Net P&L" 
          value={`${stats.totalPnl >= 0 ? '+' : ''}$${stats.totalPnl.toFixed(2)}`}
          color={stats.totalPnl >= 0 ? 'green' : 'red'}
        />
      </div>

      {/* Filters */}
      <div className="synchro-card p-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-synchro-text-secondary" />
            <span className="text-sm font-medium text-synchro-text-secondary">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as any)}
              className="synchro-input w-auto px-3 py-2 text-sm"
            >
              <option value="all">All</option>
              <option value="open">Open</option>
              <option value="breakeven">Breakeven</option>
              <option value="trailing">Trailing</option>
              <option value="closed">Closed</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-synchro-text-secondary">Sort:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="synchro-input w-auto px-3 py-2 text-sm"
            >
              <option value="openedAt">Date</option>
              <option value="pnl">P&L</option>
              <option value="symbol">Symbol</option>
            </select>
            <button
              onClick={() => setSortDir(d => d === 'asc' ? 'desc' : 'asc')}
              className="p-2 rounded-lg hover:bg-synchro-border transition-colors"
            >
              {sortDir === 'asc' ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>

      {/* Trade Cards */}
      <div className="space-y-4">
        {filteredTrades.length === 0 ? (
          <div className="synchro-card p-12 text-center">
            <Filter className="w-16 h-16 text-synchro-border mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-synchro-text-primary mb-2">No trades found</h3>
            <p className="text-synchro-text-secondary">Adjust filters or wait for SYNCHRO to find setups</p>
          </div>
        ) : (
          filteredTrades.map((trade, index) => (
            <TradeCardExpanded key={trade.id} trade={trade} index={index} />
          ))
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, icon, color }: { label: string; value: string | number; icon?: React.ReactNode; color?: 'blue' | 'green' | 'red' }) {
  const colorMap = {
    blue: 'text-blue-600',
    green: 'text-green-600',
    red: 'text-red-600',
  };
  return (
    <div className="synchro-card p-4">
      <p className="text-xs font-medium text-synchro-text-secondary uppercase tracking-wider">{label}</p>
      <div className="flex items-end justify-between mt-2">
        <p className={cn('text-2xl font-bold text-synchro-text-primary', color && colorMap[color])}>{value}</p>
        {icon && <div className="text-synchro-text-secondary">{icon}</div>}
      </div>
    </div>
  );
}

function TradeCardExpanded({ trade, index }: { trade: Trade; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const pnl = trade.pnl || 0;
  const isWin = pnl > 0;

  const getStatusConfig = (status: Trade['status']) => {
    switch (status) {
      case 'open':
        return { label: 'Open', color: 'bg-blue-100 text-blue-800 border-blue-200', icon: '🔍' };
      case 'breakeven':
        return { label: 'Breakeven', color: 'bg-amber-100 text-amber-800 border-amber-200', icon: '🛡️' };
      case 'trailing':
        return { label: 'Trailing', color: 'bg-green-100 text-green-800 border-green-200', icon: '🔒' };
      case 'closed':
        return { label: isWin ? 'Win' : pnl < 0 ? 'Loss' : 'Breakeven', 
          color: isWin ? 'bg-green-100 text-green-800 border-green-200' : pnl < 0 ? 'bg-red-100 text-red-800 border-red-200' : 'bg-gray-100 text-gray-800 border-gray-200',
          icon: isWin ? '✅' : pnl < 0 ? '❌' : '➖' };
    }
  };

  const statusConfig = getStatusConfig(trade.status);

  return (
    <div className="synchro-card animate-slide-up" style={{ animationDelay: `${index * 50}ms` }}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 hover:bg-synchro-border/50 transition-colors flex items-center justify-between gap-4"
      >
        <div className="flex items-center gap-4 flex-1 min-w-0">
          <div className={cn(
            'w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 text-2xl',
            trade.direction === 'buy' ? 'bg-green-100' : 'bg-red-100'
          )}>
            {trade.direction === 'buy' ? '⬆️' : '⬇️'}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="font-semibold text-synchro-text-primary truncate">{trade.symbol}</span>
              <span className={cn(
                'inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium border',
                statusConfig.color
              )}>
                {statusConfig.icon} {statusConfig.label}
              </span>
              <span className="text-xs font-medium px-2 py-1 rounded bg-synchro-border text-synchro-text-secondary">
                {trade.scoreComponents?.total || 5}/5
              </span>
            </div>
            <p className="text-sm text-synchro-text-secondary mt-1">
              {trade.direction.toUpperCase()} @ {trade.entryPrice} • {trade.lots} lots • SL: {trade.slCurrent || trade.slInitial} • TP: {trade.tp}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-4 flex-shrink-0">
          <div className="text-right">
            <p className={cn(
              'font-semibold text-lg',
              isWin ? 'text-green-600' : pnl < 0 ? 'text-red-600' : 'text-synchro-text-primary'
            )}>
              {pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}
            </p>
            <p className="text-xs text-synchro-text-secondary">
              Opened: {new Date(trade.openedAt).toLocaleDateString()}
            </p>
          </div>
          <span className={cn(
            'text-synchro-text-secondary transition-transform duration-200',
            expanded && 'rotate-180'
          )}>
            <ChevronDown className="w-5 h-5" />
          </span>
        </div>
      </button>

      {expanded && (
        <div className="bg-synchro-border/30 border-t border-synchro-border animate-fade-in">
          <div className="p-4 grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <DetailRow label="Entry Price" value={trade.entryPrice.toFixed(5)} />
            <DetailRow label="Current SL" value={(trade.slCurrent || trade.slInitial).toFixed(5)} />
            <DetailRow label="Take Profit" value={trade.tp.toFixed(5)} />
            <DetailRow label="Position Size" value={`${trade.lots} lots`} />
            <DetailRow label="Opened" value={new Date(trade.openedAt).toLocaleString()} />
            <DetailRow label="Closed" value={trade.closedAt ? new Date(trade.closedAt).toLocaleString() : '—'} />
            <DetailRow label="Unrealized P&L" value={`${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}`} />
            <DetailRow label="Risk:Reward" value={`${((trade.tp - trade.entryPrice) / (trade.entryPrice - (trade.slCurrent || trade.slInitial))).toFixed(1)}:1`} />
          </div>

          <div className="px-4 pb-4 space-y-4">
            <div>
              <h4 className="text-sm font-semibold text-synchro-text-primary mb-3">Why this trade (3-bullet summary)</h4>
              <ul className="space-y-3 text-sm text-synchro-text-secondary">
                <li className="flex items-start gap-3 p-3 bg-white/50 rounded-xl">
                  <span className="text-lg">🎯</span>
                  <div>
                    <strong className="text-synchro-text-primary">Entry Reason:</strong>
                    <p className="mt-1">5/5 APEX score achieved — Regime: {trade.filtersSnapshot?.regime_allowed ? '✅' : '❌'}, Trend: {trade.filtersSnapshot?.trend_aligned ? '✅' : '❌'}, Momentum: {trade.filtersSnapshot?.momentum_ok ? '✅' : '❌'}, Structure: {trade.filtersSnapshot?.structure_ok ? '✅' : '❌'}, Trigger: {trade.filtersSnapshot?.trigger_fired ? '✅' : '❌'}</p>
                  </div>
                </li>
                <li className="flex items-start gap-3 p-3 bg-white/50 rounded-xl">
                  <span className="text-lg">{trade.status === 'open' ? '⚔️' : trade.status === 'breakeven' ? '🛡️' : '🔒'}</span>
                  <div>
                    <strong className="text-synchro-text-primary">Protection Status:</strong>
                    <p className="mt-1">
                      {trade.status === 'open' 
                        ? `Initial stop loss at ${trade.slInitial} (${((trade.entryPrice - trade.slInitial) / trade.entryPrice * 100).toFixed(1)}% risk)`
                        : trade.status === 'breakeven'
                          ? `Breakeven activated — SL moved to entry (${trade.slCurrent}) +10 pips`
                          : `Trailing active — SL at ${trade.slCurrent}, profit locked`}
                    </p>
                  </div>
                </li>
                <li className="flex items-start gap-3 p-3 bg-white/50 rounded-xl">
                  <span className="text-lg">📚</span>
                  <div>
                    <strong className="text-synchro-text-primary">Learning Note:</strong>
                    <p className="mt-1">Pattern logged to database — Regime: {trade.filtersSnapshot?.regime_allowed ? 'passed' : 'failed'}, Outcome will update win-rate statistics for future threshold optimization</p>
                  </div>
                </li>
              </ul>
            </div>

            <div className="pt-4 border-t border-synchro-border">
              <h4 className="text-sm font-semibold text-synchro-text-primary mb-3">Score Breakdown</h4>
              <div className="grid grid-cols-5 gap-2">
                <ScorePill label="Regime" value={trade.scoreComponents?.regime || 1} max={1} />
                <ScorePill label="Trend" value={trade.scoreComponents?.trend || 1} max={1} />
                <ScorePill label="Momentum" value={trade.scoreComponents?.momentum || 1} max={1} />
                <ScorePill label="Structure" value={trade.scoreComponents?.structure || 1} max={1} />
                <ScorePill label="Trigger" value={trade.scoreComponents?.trigger || 1} max={1} />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs font-medium text-synchro-text-secondary uppercase tracking-wider">{label}</span>
      <span className="text-sm font-semibold text-synchro-text-primary">{value}</span>
    </div>
  );
}

function ScorePill({ label, value, max }: { label: string; value: number; max: number }) {
  const isPassed = value >= max;
  return (
    <div className="text-center p-3 bg-white/50 rounded-xl">
      <div className={cn(
        'w-10 h-10 rounded-full flex items-center justify-center mx-auto mb-2 font-bold text-lg',
        isPassed ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
      )}>
        {value}/{max}
      </div>
      <span className="text-[11px] font-medium text-synchro-text-secondary uppercase tracking-wider">{label}</span>
    </div>
  );
}