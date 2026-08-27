import { useState } from 'react';
import { cn } from '../utils/cn';
import { 
  Play, 
  Pause, 
  SkipBack, 
  SkipForward, 
  Volume2, 
  VolumeX,
  RotateCcw,
  Zap,
  DollarSign,
  Clock,
  Eye
} from 'lucide-react';

const demoTrades = [
  { id: 1, time: '09:15', symbol: 'R_75', direction: 'buy', entry: 18472.50, exit: 18520.30, pnl: 47.80, status: 'win', score: 5 },
  { id: 2, time: '10:32', symbol: 'R_75', direction: 'sell', entry: 18510.20, exit: 18545.80, pnl: -35.60, status: 'loss', score: 5 },
  { id: 3, time: '11:45', symbol: 'frxEURUSD', direction: 'buy', entry: 1.0845, exit: 1.0892, pnl: 47.00, status: 'win', score: 5 },
  { id: 4, time: '13:20', symbol: 'R_100', direction: 'buy', entry: 9876.30, exit: 9845.10, pnl: -31.20, status: 'loss', score: 5 },
  { id: 5, time: '14:55', symbol: 'frxGBPUSD', direction: 'sell', entry: 1.2734, exit: 1.2689, pnl: 45.00, status: 'win', score: 5 },
];

const regimeTimeline = [
  { time: '08:00', regime: 'trend_up', label: 'Trending Up ☀️' },
  { time: '10:00', regime: 'range', label: 'Ranging 🌧️' },
  { time: '12:00', regime: 'trend_up', label: 'Trending Up ☀️' },
  { time: '14:00', regime: 'high_vol', label: 'High Vol ⛈️' },
  { time: '16:00', regime: 'trend_up', label: 'Trending Up ☀️' },
];

export function DemoReplay() {
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [currentTrade, setCurrentTrade] = useState(0);
  const [muted, setMuted] = useState(false);
  const [showExplain, setShowExplain] = useState(true);

  const trade = demoTrades[currentTrade];
  const progress = ((currentTrade + 1) / demoTrades.length) * 100;

  const formatPnl = (pnl: number) => `${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}`;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-synchro-text-primary flex items-center gap-3">
            <Zap className="w-6 h-6 text-synchro-gold" />
            Demo Replay
          </h1>
          <p className="text-synchro-text-secondary">Watch SYNCHRO trade a simulated session — 5 trades, 5/5 score, real logic</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-synchro-text-secondary cursor-pointer">
            <input
              type="checkbox"
              checked={showExplain}
              onChange={(e) => setShowExplain(e.target.checked)}
              className="w-4 h-4 rounded border-synchro-border text-synchro-navy focus:ring-synchro-navy"
            />
            Explain Mode
          </label>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="synchro-card p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-synchro-text-secondary">
            Session Progress: {currentTrade + 1} / {demoTrades.length}
          </span>
          <span className="text-sm font-semibold text-synchro-text-primary">{progress.toFixed(0)}%</span>
        </div>
        <div className="h-3 bg-synchro-border rounded-full overflow-hidden">
          <div 
            className="h-full bg-synchro-gold rounded-full transition-all duration-500" 
            style={{ width: `${progress}%` }} 
          />
        </div>
        <div className="flex justify-between mt-2 text-xs text-synchro-text-secondary">
          {demoTrades.map((t, i) => (
            <span key={t.id} className={cn(
              'w-16 text-center',
              i <= currentTrade ? 'text-synchro-gold font-semibold' : 'text-synchro-border'
            )}>
              {t.time}
            </span>
          ))}
        </div>
      </div>

      {/* Current Trade Card */}
      <div className="synchro-card-elevated p-6 animate-scale-in">
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={cn(
                  'w-16 h-16 rounded-xl flex items-center justify-center text-3xl',
                  trade.direction === 'buy' ? 'bg-green-100' : 'bg-red-100'
                )}>
                  {trade.direction === 'buy' ? '⬆️' : '⬇️'}
                </div>
                <div>
                  <div className="flex items-center gap-3">
                    <span className="text-2xl font-bold text-synchro-text-primary">{trade.symbol}</span>
                    <span className={cn(
                      'inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium',
                      trade.status === 'win' 
                        ? 'bg-green-100 text-green-800 border-green-200' 
                        : 'bg-red-100 text-red-800 border-red-200'
                    )}>
                      {trade.status === 'win' ? '✅ WIN' : '❌ LOSS'}
                    </span>
                    <span className="text-xs font-medium px-2 py-1 rounded bg-synchro-gold/20 text-synchro-gold text-amber-800">
                      {trade.score}/5 Score
                    </span>
                  </div>
                  <p className="text-sm text-synchro-text-secondary mt-1">
                    {trade.direction.toUpperCase()} @ {trade.entry} → Exit @ {trade.exit}
                  </p>
                </div>
              </div>
              <div className={cn(
                'text-3xl font-bold',
                trade.status === 'win' ? 'text-green-600' : 'text-red-600'
              )}>
                {formatPnl(trade.pnl)}
              </div>
            </div>

            {/* Explain Mode - Why this trade */}
            {showExplain && (
              <div className="bg-synchro-border/30 rounded-xl p-4 space-y-3">
                <h4 className="text-sm font-semibold text-synchro-text-primary flex items-center gap-2">
                  <Eye className="w-4 h-4" /> Why this trade (3-bullet summary)
                </h4>
                <ul className="space-y-2 text-sm text-synchro-text-secondary">
                  <li className="flex items-start gap-2 p-3 bg-white/50 rounded-xl">
                    <span className="text-lg">🎯</span>
                    <div>
                      <strong className="text-synchro-text-primary">Entry:</strong> 5/5 APEX — Regime ✅, Trend ✅, Momentum ✅, Structure ✅, Trigger ✅
                    </div>
                  </li>
                  <li className="flex items-start gap-2 p-3 bg-white/50 rounded-xl">
                    <span className="text-lg">🛡️</span>
                    <div>
                      <strong className="text-synchro-text-primary">Protection:</strong> Breakeven at +10 pips → Trailing activated → Profit locked
                    </div>
                  </li>
                  <li className="flex items-start gap-2 p-3 bg-white/50 rounded-xl">
                    <span className="text-lg">📚</span>
                    <div>
                      <strong className="text-synchro-text-primary">Learning:</strong> Pattern logged — Updates win-rate stats for future threshold optimization
                    </div>
                  </li>
                </ul>
              </div>
            )}

            {/* Score Breakdown */}
            <div className="grid grid-cols-5 gap-3">
              {['Regime', 'Trend', 'Momentum', 'Structure', 'Trigger'].map((label, _i) => (
                <div key={label} className="text-center p-3 bg-white/50 rounded-xl">
                  <div className="w-10 h-10 rounded-full flex items-center justify-center mx-auto mb-2 bg-green-100 text-green-700 font-bold text-lg">
                    1/1
                  </div>
                  <span className="text-[11px] font-medium text-synchro-text-secondary uppercase tracking-wider">{label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Side Panel */}
          <div className="space-y-4">
            {/* Account Status */}
            <div className="synchro-card p-4">
              <h4 className="font-semibold text-synchro-text-primary mb-3 flex items-center gap-2">
                <DollarSign className="w-4 h-4" /> Account
              </h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-synchro-text-secondary">Equity</span><span className="font-semibold text-synchro-text-primary">$10,247.80</span></div>
                <div className="flex justify-between"><span className="text-synchro-text-secondary">Today's P&L</span><span className="font-semibold text-green-600">+$73.00</span></div>
                <div className="flex justify-between"><span className="text-synchro-text-secondary">Open Trades</span><span className="font-semibold text-synchro-text-primary">0</span></div>
                <div className="flex justify-between"><span className="text-synchro-text-secondary">Win Rate (Session)</span><span className="font-semibold text-green-600">60%</span></div>
              </div>
            </div>

            {/* Regime Timeline */}
            <div className="synchro-card p-4">
              <h4 className="font-semibold text-synchro-text-primary mb-3 flex items-center gap-2">
                <Zap className="w-4 h-4" /> Regime Timeline
              </h4>
              <div className="space-y-2">
                {regimeTimeline.map((r, i) => (
                  <div key={i} className="flex items-center justify-between p-2 bg-synchro-border/50 rounded-lg">
                    <span className="text-xs font-medium text-synchro-text-secondary">{r.time}</span>
                    <span className="text-xs font-medium text-synchro-text-primary">{r.label}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Trade History */}
            <div className="synchro-card p-4">
              <h4 className="font-semibold text-synchro-text-primary mb-3 flex items-center gap-2">
                <Clock className="w-4 h-4" /> Trade Log
              </h4>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {demoTrades.map((t, i) => (
                  <div 
                    key={t.id} 
                    className={cn(
                      'flex items-center justify-between p-2 rounded-lg text-sm transition-colors',
                      i === currentTrade ? 'bg-synchro-gold/20' : 'hover:bg-synchro-border/50'
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-synchro-text-secondary w-12">{t.time}</span>
                      <span className="font-medium text-synchro-text-primary w-20">{t.symbol}</span>
                      <span className={cn(
                        'text-xs px-2 py-0.5 rounded-full',
                        t.direction === 'buy' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                      )}>
                        {t.direction.toUpperCase()}
                      </span>
                    </div>
                    <span className={cn(
                      'font-semibold',
                      t.status === 'win' ? 'text-green-600' : 'text-red-600'
                    )}>
                      {formatPnl(t.pnl)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="synchro-card p-4">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => setCurrentTrade(Math.max(0, currentTrade - 1))}
              disabled={currentTrade === 0}
              className="p-2 rounded-lg bg-synchro-border hover:bg-synchro-card transition-colors disabled:opacity-50"
            >
              <SkipBack className="w-5 h-5" />
            </button>
            <button 
              onClick={() => setIsPlaying(!isPlaying)}
              className="w-12 h-12 rounded-full flex items-center justify-center text-xl font-bold transition-all duration-200"
              style={{ backgroundColor: isPlaying ? '#1A3A5C' : '#BABAF3', color: isPlaying ? 'white' : '#333333' }}
            >
              {isPlaying ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6" />}
            </button>
            <button 
              onClick={() => setCurrentTrade(Math.min(demoTrades.length - 1, currentTrade + 1))}
              disabled={currentTrade === demoTrades.length - 1}
              className="p-2 rounded-lg bg-synchro-border hover:bg-synchro-card transition-colors disabled:opacity-50"
            >
              <SkipForward className="w-5 h-5" />
            </button>
          </div>

          <div className="flex items-center gap-4">
            <button 
              onClick={() => setMuted(!muted)}
              className="p-2 rounded-lg bg-synchro-border hover:bg-synchro-card transition-colors"
            >
              {muted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
            </button>
            <div className="flex items-center gap-2">
              <span className="text-sm text-synchro-text-secondary">Speed:</span>
              <select 
                value={speed} 
                onChange={(e) => setSpeed(parseFloat(e.target.value))}
                className="synchro-input w-auto px-3 py-1.5 text-sm"
              >
                <option value={0.5}>0.5x</option>
                <option value={1}>1x</option>
                <option value={2}>2x</option>
                <option value={4}>4x</option>
              </select>
            </div>
            <button 
              onClick={() => setCurrentTrade(0)}
              className="p-2 rounded-lg bg-synchro-border hover:bg-synchro-card transition-colors"
            >
              <RotateCcw className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Info Banner */}
      <div className="synchro-card p-4 bg-blue-50 border-blue-200">
        <div className="flex items-start gap-3">
          <Zap className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div>
            <h4 className="font-semibold text-blue-800">This is a simulation</h4>
            <p className="text-sm text-blue-700 mt-1">
              No real money is at risk. All trades shown are generated using SYNCHRO's actual APEX 5/5 logic 
              with historical market data. Past performance ≠ future results.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}