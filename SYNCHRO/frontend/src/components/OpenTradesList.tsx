import type { Trade } from '../types';
import { cn } from '../utils/cn';
import { Shield, Lock, TrendingUp, TrendingDown, X } from 'lucide-react';
import { useState } from 'react';

interface OpenTradesListProps {
  trades: Trade[];
}

export function OpenTradesList({ trades }: OpenTradesListProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (!trades.length) {
    return (
      <div className="synchro-card p-8 text-center">
        <div className="w-16 h-16 rounded-full bg-synchro-border flex items-center justify-center mx-auto mb-4">
          <X className="w-8 h-8 text-synchro-text-secondary" />
        </div>
        <h3 className="text-lg font-semibold text-synchro-text-primary mb-2">No open trades</h3>
        <p className="text-synchro-text-secondary">SYNCHRO is watching for 5/5 setups</p>
      </div>
    );
  }

  const getStatusBadge = (status: Trade['status']) => {
    switch (status) {
      case 'open':
        return <span className="synchro-badge synchro-badge-info">Open</span>;
      case 'breakeven':
        return (
          <span className="synchro-badge synchro-badge-gold flex items-center gap-1">
            <Shield className="w-3 h-3" /> Protected ✓
          </span>
        );
      case 'trailing':
        return (
          <span className="synchro-badge synchro-badge-success flex items-center gap-1">
            <Lock className="w-3 h-3" /> Profit Locked 🔒
          </span>
        );
      case 'closed':
        return <span className="synchro-badge synchro-badge-success">Closed</span>;
    }
  };

  const getDirectionIcon = (direction: Trade['direction']) => 
    direction === 'buy' ? (
      <TrendingUp className="w-4 h-4 text-green-600" />
    ) : (
      <TrendingDown className="w-4 h-4 text-red-600" />
    );

  return (
    <div className="synchro-card">
      <div className="p-4 border-b border-synchro-border flex items-center justify-between">
        <h3 className="text-lg font-semibold text-synchro-text-primary">Open Trades</h3>
        <span className="synchro-badge synchro-badge-info">{trades.length} active</span>
      </div>
      <div className="divide-y divide-synchro-border">
        {trades.map((trade) => (
          <TradeCard 
            key={trade.id} 
            trade={trade} 
            isExpanded={expandedId === trade.id}
            onToggle={() => setExpandedId(expandedId === trade.id ? null : trade.id)}
            getStatusBadge={getStatusBadge}
            getDirectionIcon={getDirectionIcon}
          />
        ))}
      </div>
    </div>
  );
}

interface TradeCardProps {
  trade: Trade;
  isExpanded: boolean;
  onToggle: () => void;
  getStatusBadge: (status: Trade['status']) => React.ReactNode;
  getDirectionIcon: (direction: Trade['direction']) => React.ReactNode;
}

function TradeCard({ trade, isExpanded, onToggle, getStatusBadge, getDirectionIcon }: TradeCardProps) {
  const pnl = trade.pnl || 0;
  const isWin = pnl > 0;
  const unrealizedPnl = trade.exitPrice 
    ? (trade.direction === 'buy' ? trade.exitPrice - trade.entryPrice : trade.entryPrice - trade.exitPrice) * trade.lots * 100
    : pnl;

  return (
    <div className="animate-slide-up">
      <button
        onClick={onToggle}
        className="w-full p-4 hover:bg-synchro-border/50 transition-colors flex items-center justify-between gap-4"
        aria-expanded={isExpanded}
      >
        <div className="flex items-center gap-4 flex-1 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-synchro-card flex items-center justify-center flex-shrink-0">
            {getDirectionIcon(trade.direction)}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-synchro-text-primary truncate">{trade.symbol}</span>
              {getStatusBadge(trade.status)}
            </div>
            <p className="text-sm text-synchro-text-secondary">
              {trade.direction.toUpperCase()} @ {trade.entryPrice} • {trade.lots} lots
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-4 flex-shrink-0">
          <div className="text-right">
            <p className={cn(
              'font-semibold',
              isWin ? 'text-green-600' : pnl < 0 ? 'text-red-600' : 'text-synchro-text-primary'
            )}>
              ${unrealizedPnl.toFixed(2)}
            </p>
            <p className="text-xs text-synchro-text-secondary">
              SL: {trade.slCurrent || trade.slInitial} • TP: {trade.tp}
            </p>
          </div>
          <span className="text-synchro-text-secondary">Score: {trade.scoreComponents?.total || 5}/5</span>
        </div>
      </button>

      {isExpanded && (
        <div className="bg-synchro-border/30 p-4 border-t border-synchro-border animate-fade-in">
          <div className="grid sm:grid-cols-2 gap-4 mb-4">
            <DetailRow label="Entry Price" value={trade.entryPrice.toFixed(5)} />
            <DetailRow label="Current SL" value={(trade.slCurrent || trade.slInitial).toFixed(5)} />
            <DetailRow label="Take Profit" value={trade.tp.toFixed(5)} />
            <DetailRow label="Position Size" value={`${trade.lots} lots`} />
            <DetailRow label="Opened" value={new Date(trade.openedAt).toLocaleString()} />
            <DetailRow label="Unrealized P&L" value={`${unrealizedPnl >= 0 ? '+' : ''}$${unrealizedPnl.toFixed(2)}`} />
          </div>
          
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-synchro-text-primary">Why this trade (3-bullet summary)</h4>
            <ul className="space-y-2 text-sm text-synchro-text-secondary">
              <li className="flex items-center gap-2">🎯 <strong>Entry:</strong> 5/5 APEX score — regime aligned, trend confirmed, momentum positive, structure clean, trigger fired</li>
              <li className="flex items-center gap-2">{trade.status === 'breakeven' || trade.status === 'trailing' ? '🛡️' : '⚔️'} <strong>Protection:</strong> {trade.status === 'open' ? 'Initial SL active' : trade.status === 'breakeven' ? 'Breakeven set (+10 pips)' : 'Trailing active — profit locked'}</li>
              <li className="flex items-center gap-2">📚 <strong>Learning:</strong> Pattern logged — {trade.filtersSnapshot?.regime_allowed ? 'regime filter passed' : 'regime filter failed'}</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between py-1">
      <span className="text-sm text-synchro-text-secondary">{label}</span>
      <span className="text-sm font-medium text-synchro-text-primary">{value}</span>
    </div>
  );
}