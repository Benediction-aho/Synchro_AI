import { useState } from 'react';
import { useApp } from '../context/AppContext';
import { 
  Maximize2,
  Minimize2,
  HelpCircle,
  Info
} from 'lucide-react';
import { cn } from '../utils/cn';
import { CandlestickChart } from '../components/CandlestickChart';
import { MarketStatusCards } from '../components/MarketStatusCards';

const timeframes = ['1m', '5m', '15m', '1H', '4H', '1D'] as const;
type Timeframe = typeof timeframes[number];

export function LiveCharts() {
  const { marketData, explainMode } = useApp();
  const [selectedSymbol, setSelectedSymbol] = useState('R_75');
  const [timeframe, setTimeframe] = useState<Timeframe>('15m');
  const [showIndicators, setShowIndicators] = useState(true);
  const [expanded, setExpanded] = useState(false);

  const market = marketData.find(m => m.symbol === selectedSymbol) || 
    { symbol: 'R_75', regime: 'trend_up', trend: 'bullish', momentum: 0.65, rsi: 58, price: 18472.50, change24h: 2.3 };

  const regimeInfo = {
    trend_up: { label: 'Trending Up ☀️', desc: 'Market is trending upward — SYNCHRO looks for pullback entries', color: 'text-green-600' },
    trend_down: { label: 'Trending Down ☀️', desc: 'Market is trending downward — SYNCHRO looks for rally shorts', color: 'text-red-600' },
    range: { label: 'Ranging 🌧️', desc: 'Market is resting — SYNCHRO waits for breakout', color: 'text-blue-600' },
    high_vol: { label: 'High Volatility ⛈️', desc: 'Choppy conditions — SYNCHRO reduces position size', color: 'text-purple-600' },
    crisis: { label: 'Crisis 🚨', desc: 'Extreme conditions — SYNCHRO halts trading', color: 'text-red-800' },
  }[market.regime];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-synchro-text-primary">Live Charts</h1>
          <p className="text-synchro-text-secondary">Real-time market analysis with APEX signal overlay</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={selectedSymbol}
            onChange={(e) => setSelectedSymbol(e.target.value)}
            className="synchro-input w-auto px-3 py-2 text-sm"
          >
            {['R_75', 'R_100', 'frxEURUSD', 'frxGBPUSD', 'frxUSDJPY'].map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <div className="flex bg-synchro-border rounded-xl p-1" role="group">
            {timeframes.map(tf => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={cn(
                  'px-3 py-1.5 text-sm font-medium rounded-lg transition-all',
                  timeframe === tf 
                    ? 'bg-synchro-navy text-white' 
                    : 'text-synchro-text-secondary hover:text-synchro-text-primary'
                )}
              >
                {tf}
              </button>
            ))}
          </div>
          <button
            onClick={() => setExpanded(!expanded)}
            className="synchro-btn-secondary px-4 py-2"
          >
            {expanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Market Status Bar */}
      <div className="grid lg:grid-cols-5 gap-4">
        <div className="synchro-card p-4 lg:col-span-2">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-synchro-text-secondary uppercase tracking-wider">HMM Regime</span>
            <span className={cn('text-2xl', regimeInfo.color)}>{regimeInfo.label.split(' ').pop()}</span>
          </div>
          <p className={cn('text-lg font-semibold', regimeInfo.color)}>{regimeInfo.label}</p>
          {explainMode && (
            <p className="mt-2 text-sm text-synchro-text-secondary flex items-center gap-1">
              <Info className="w-4 h-4" /> {regimeInfo.desc}
            </p>
          )}
        </div>
        <div className="synchro-card p-4">
          <p className="text-xs font-medium text-synchro-text-secondary uppercase tracking-wider">Trend</p>
          <p className="text-lg font-semibold mt-1 capitalize">{market.trend}</p>
        </div>
        <div className="synchro-card p-4">
          <p className="text-xs font-medium text-synchro-text-secondary uppercase tracking-wider">Momentum</p>
          <p className="text-lg font-semibold mt-1">{(market.momentum * 100).toFixed(0)}%</p>
        </div>
        <div className="synchro-card p-4">
          <p className="text-xs font-medium text-synchro-text-secondary uppercase tracking-wider">RSI</p>
          <p className="text-lg font-semibold mt-1">{market.rsi}</p>
        </div>
      </div>

      {/* Main Chart */}
      <div className={cn(
        'synchro-card overflow-hidden transition-all duration-300',
        expanded ? 'lg:fixed lg:inset-4 lg:z-50 lg:m-4' : ''
      )}>
        <div className="p-4 border-b border-synchro-border flex items-center justify-between">
          <h2 className="text-lg font-semibold text-synchro-text-primary">
            {selectedSymbol} • {timeframe} Candles
          </h2>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-synchro-text-secondary cursor-pointer">
              <input
                type="checkbox"
                checked={showIndicators}
                onChange={(e) => setShowIndicators(e.target.checked)}
                className="w-4 h-4 rounded border-synchro-border text-synchro-navy focus:ring-synchro-navy"
              />
              Show APEX Signals
            </label>
            {explainMode && (
              <HelpCircle className="w-4 h-4 text-synchro-text-secondary" aria-label="Green=Buy, Red=Sell, Gray=Wait" />
            )}
          </div>
        </div>
        <div className={cn('h-[500px] lg:h-[600px]', expanded && 'h-[calc(100vh-8rem)]')}>
          <CandlestickChart 
            symbol={selectedSymbol} 
            showSignals={showIndicators}
            regime={market.regime}
          />
        </div>
      </div>

      {/* Market Overview */}
      <MarketStatusCards data={[]} />
    </div>
  );
}