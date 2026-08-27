import { useApp } from '../context/AppContext';
import type { ApprovalRequest, ApprovalStatus } from '../types';
import { cn } from '../utils/cn';
import { 
  CheckCircle2, 
  XCircle, 
  Clock, 
  AlertTriangle, 
  Shield,
  Zap
} from 'lucide-react';
import { useState, useEffect } from 'react';

const statusConfig: Record<ApprovalStatus, { label: string; color: string; icon: React.ReactNode }> = {
  pending: { label: 'Pending', color: 'text-amber-600 bg-amber-100 border-amber-200', icon: <Clock className="w-4 h-4" /> },
  approved: { label: 'Approved', color: 'text-green-600 bg-green-100 border-green-200', icon: <CheckCircle2 className="w-4 h-4" /> },
  declined: { label: 'Declined', color: 'text-red-600 bg-red-100 border-red-200', icon: <XCircle className="w-4 h-4" /> },
  timeout: { label: 'Timed Out', color: 'text-gray-600 bg-gray-100 border-gray-200', icon: <Clock className="w-4 h-4" /> },
};

const typeConfig: Record<ApprovalRequest['type'], { label: string; icon: React.ReactNode; color: string }> = {
  evolution: { label: 'Evolution Update', icon: <Zap className="w-4 h-4" />, color: 'text-purple-600' },
  trade_override: { label: 'Trade Override', icon: <Shield className="w-4 h-4" />, color: 'text-orange-600' },
  risk_change: { label: 'Risk Change', icon: <AlertTriangle className="w-4 h-4" />, color: 'text-red-600' },
};

export function ApprovalCenter() {
  const { approvals, addApproval } = useApp();
  const [filter, setFilter] = useState<ApprovalStatus | 'all'>('all');

  // Add demo approvals if empty
  useEffect(() => {
    if (approvals.length === 0) {
      const demoApprovals: ApprovalRequest[] = [
        {
          id: 'appr-1',
          type: 'evolution',
          title: 'New Model Version v2024-01-15',
          details: {
            'Sharpe Improvement': '+12.3%',
            'Win Rate': '58.4% → 62.1%',
            'Max Drawdown': '8.2% → 6.7%',
            'New Min Score': '5/5 (unchanged)',
            'Risk/Trade': '1.0% → 1.2%',
          },
          createdAt: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
          expiresAt: new Date(Date.now() + 10 * 60 * 1000).toISOString(),
          status: 'pending',
        },
        {
          id: 'appr-2',
          type: 'trade_override',
          title: 'Manual Trade Override Request',
          details: {
            'Symbol': 'frxEURUSD',
            'Direction': 'BUY',
            'Entry': '1.0845',
            'Size': '0.15 lots',
            'Reason': 'News event override',
            'Requested By': 'System',
          },
          createdAt: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
          expiresAt: new Date(Date.now() + 13 * 60 * 1000).toISOString(),
          status: 'pending',
        },
        {
          id: 'appr-3',
          type: 'risk_change',
          title: 'Risk Phase Increase',
          details: {
            'Current Phase': 'Phase 2',
            'Proposed Phase': 'Phase 3',
            'Capital Increase': '$10,000 → $15,000',
            'Reason': 'Consistent 60%+ win rate over 30 days',
          },
          createdAt: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
          expiresAt: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
          status: 'timeout',
        },
      ];
      demoApprovals.forEach(a => addApproval(a));
    }
  }, [approvals.length, addApproval]);

  const filtered = filter === 'all' ? approvals : approvals.filter(a => a.status === filter);
  const pendingCount = approvals.filter(a => a.status === 'pending').length;

  const handleDecision = (id: string, approved: boolean) => {
    addApproval({ ...approvals.find(a => a.id === id)!, status: approved ? 'approved' : 'declined', approved, decidedAt: new Date().toISOString() });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-synchro-text-primary">Approval Center</h1>
          <p className="text-synchro-text-secondary">Review and decide on evolution updates, trade overrides, and risk changes</p>
        </div>
        <div className="flex items-center gap-3">
          {pendingCount > 0 && (
            <span className="synchro-badge synchro-badge-warning flex items-center gap-1 animate-pulse">
              <Clock className="w-3 h-3" />
              {pendingCount} pending
            </span>
          )}
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 bg-synchro-border rounded-xl p-1" role="tablist">
        {(['all', 'pending', 'approved', 'declined', 'timeout'] as const).map(status => (
          <button
            key={status}
            role="tab"
            aria-selected={filter === status}
            onClick={() => setFilter(status)}
            className={cn(
              'px-4 py-2 text-sm font-medium rounded-lg transition-all',
              filter === status 
                ? 'bg-white text-synchro-navy shadow-sm' 
                : 'text-synchro-text-secondary hover:text-synchro-text-primary'
            )}
          >
            {status !== 'all' ? statusConfig[status].icon : <Clock className="w-4 h-4" />}
            <span className="ml-2 capitalize">{status}</span>
            {status !== 'all' && approvals.filter(a => a.status === status).length > 0 && (
              <span className="ml-2 px-1.5 py-0.5 text-xs rounded-full bg-synchro-border">
                {approvals.filter(a => a.status === status).length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Approval Cards */}
      <div className="space-y-4">
        {filtered.length === 0 ? (
          <div className="synchro-card p-12 text-center">
            <CheckCircle2 className="w-16 h-16 text-synchro-border mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-synchro-text-primary mb-2">No approvals found</h3>
            <p className="text-synchro-text-secondary">All caught up! New requests will appear here.</p>
          </div>
        ) : (
          filtered.map((approval) => (
            <ApprovalCard 
              key={approval.id} 
              approval={approval} 
              onApprove={() => handleDecision(approval.id, true)}
              onDecline={() => handleDecision(approval.id, false)}
            />
          ))
        )}
      </div>
    </div>
  );
}

function ApprovalCard({ 
  approval, 
  onApprove, 
  onDecline 
}: { 
  approval: ApprovalRequest; 
  onApprove: () => void; 
  onDecline: () => void;
}) {
  const [timeLeft, setTimeLeft] = useState(0);
  const statusInfo = statusConfig[approval.status];
  const typeInfo = typeConfig[approval.type];

  useEffect(() => {
    const updateTime = () => {
      const diff = new Date(approval.expiresAt).getTime() - Date.now();
      setTimeLeft(Math.max(0, diff));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, [approval.expiresAt]);

  const minutes = Math.floor(timeLeft / 60000);
  const seconds = Math.floor((timeLeft % 60000) / 1000);
  const isExpired = timeLeft <= 0;
  const isPending = approval.status === 'pending';

  return (
    <div className={cn(
      'synchro-card overflow-hidden animate-slide-up',
      approval.status === 'pending' && 'ring-2 ring-amber-300'
    )}>
      {/* Header */}
      <div className="p-4 border-b border-synchro-border flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center', `${typeInfo.color} bg-opacity-10`)}>
            {typeInfo.icon}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-synchro-text-primary">{approval.title}</h3>
              <span className={cn(
                'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border',
                statusInfo.color
              )}>
                {statusInfo.icon} {statusInfo.label}
              </span>
              <span className={cn(
                'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
                `bg-${typeInfo.color.replace('text-', '')}-100 text-${typeInfo.color.replace('text-', '')}-800`
              )}>
                {typeInfo.label}
              </span>
            </div>
            <p className="text-xs text-synchro-text-secondary">
              Created: {new Date(approval.createdAt).toLocaleString()}
            </p>
          </div>
        </div>

        {/* Countdown Ring */}
        {isPending && !isExpired && (
          <div className="relative w-20 h-20 flex items-center justify-center">
            <svg className="w-full h-full transform -rotate-90">
              <circle
                cx="50"
                cy="50"
                r="45"
                fill="none"
                stroke="#D0D0E8"
                strokeWidth="4"
              />
              <circle
                cx="50"
                cy="50"
                r="45"
                fill="none"
                stroke="#C8960C"
                strokeWidth="4"
                strokeDasharray={283}
                strokeDashoffset={283 * (1 - timeLeft / (15 * 60 * 1000))}
                strokeLinecap="round"
                className="transition-all duration-1000"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-sm font-bold text-synchro-text-primary">
                {minutes}:{seconds.toString().padStart(2, '0')}
              </span>
            </div>
          </div>
        )}

        {isExpired && isPending && (
          <div className="w-20 h-20 flex items-center justify-center">
            <span className="text-sm font-medium text-synchro-text-secondary">EXPIRED</span>
          </div>
        )}
      </div>

      {/* Details */}
      <div className="p-4 border-b border-synchro-border bg-synchro-border/30">
        <h4 className="text-sm font-semibold text-synchro-text-primary mb-3">Details</h4>
        <div className="grid sm:grid-cols-2 gap-3">
          {Object.entries(approval.details).map(([key, value]) => (
            <div key={key} className="flex items-center justify-between py-2 px-3 bg-white/50 rounded-xl">
              <span className="text-sm text-synchro-text-secondary">{key}</span>
              <span className="text-sm font-medium text-synchro-text-primary">{value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Actions */}
      {isPending && !isExpired && (
        <div className="p-4 border-t border-synchro-border flex items-center justify-end gap-3">
          <button
            onClick={onDecline}
            className="synchro-btn-secondary px-6 py-2.5"
            disabled={!isPending}
          >
            <XCircle className="w-4 h-4 mr-2" /> Decline
          </button>
          <button
            onClick={onApprove}
            className="synchro-btn-primary px-6 py-2.5"
            disabled={!isPending}
          >
            <CheckCircle2 className="w-4 h-4 mr-2" /> Approve
          </button>
        </div>
      )}

      {approval.status !== 'pending' && (
        <div className="p-4 border-t border-synchro-border bg-synchro-border/30 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {statusInfo.icon}
            <span className="text-sm font-medium text-synchro-text-secondary">
              {approval.status === 'approved' ? 'Approved' : approval.status === 'declined' ? 'Declined' : 'Timed out (auto-declined)'}
            </span>
          </div>
          {approval.decidedAt && (
            <span className="text-xs text-synchro-text-secondary">
              Decided: {new Date(approval.decidedAt).toLocaleString()}
            </span>
          )}
        </div>
      )}
    </div>
  );
}