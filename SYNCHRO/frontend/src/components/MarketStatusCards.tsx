import type { MarketData } from '../types';
import { cn } from '../utils/cn';

interface MarketStatusCardsProps {
  data: MarketData[];
}

const regimeLabels: Record<MarketData['regime'], { label: string; icon: string; color: string }> = {
  trend_up: { label: 'Trending Up', icon: '☀️', color: 'text-green-600' },
  trend_down: { label: 'Trending Down', icon: '☀️', color: 'text-red-600' },
  range: { label: 'Ranging', icon: '🌧️', color: 'text-blue-600' },
  high_vol: { label: 'High Volatility', icon: '⛈️', color: 'text-purple-600' },
  crisis: { label: 'Crisis', icon: '🚨', color: 'text-red-800' },
};

const trendLabels: Record<MarketData['trend'], { label: string; color: string }> = {
  bullish: { label: 'Bullish', color: 'text-green-600' },
  bearish: { label: 'Bearish', color: 'text-red-600' },
  neutral: { label: 'Neutral', color: 'text-gray-600' },
};

const defaultMarkets: MarketData[] = [
  { symbol: 'R_75', regime: 'trend_up', trend: 'bullish', momentum: 0.65, rsi: 58, price: 18472.50, change24h: 2.3 },
  { symbol: 'R_100', regime: 'range', trend: 'neutral', momentum: 0.12, rsi: 52, price: 9876.30, change24h: -0.5 },
  { symbol: 'frxEURUSD', regime: 'trend_up', trend: 'bullish', momentum: 0.42, rsi: 61, price: 1.0845, change24h: 0.8 },
  { symbol: 'frxGBPUSD', regime: 'high_vol', trend: 'bullish', momentum: 0.78, rsi: 68, price: 1.2734, change24h: 1.2 },
];

export function MarketStatusCards({ data }: MarketStatusCardsProps) {
  const markets = data.length ? data : defaultMarkets;

  return (
    <section aria-label="Market status overview">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {markets.map((market) => (
          <MarketCard key={market.symbol} market={market} />
        ))}
      </div>
    </section>
  );
}

function MarketCard({ market }: { market: MarketData }) {
  const regimeInfo = regimeLabels[market.regime];
  const trendInfo = trendLabels[market.trend];
  const isPositive = market.change24h >= 0;

  return (
    <div className="synchro-card p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="text-xs font-medium text-synchro-text-secondary uppercase tracking-wider">
            {market.symbol}
          </p>
          <p className="text-2xl font-bold text-synchro-text-primary mt-1">
            {market.price.toLocaleString(undefined, { minimumFractionDigits: market.symbol.startsWith('frx') ? 4 : 2 })}
          </p>
        </div>
        <span className={cn(
          'text-2xl',
          regimeInfo.color
        )}>
          {regimeInfo.icon}
        </span>
      </div>

      <div className="flex items-center justify-between text-sm mb-3">
        <span className={cn('font-medium', regimeInfo.color)}>
          {regimeInfo.label}
        </span>
        <span className={cn('font-medium', trendInfo.color)}>
          {trendInfo.label}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-3">
        <MetricMini label="Momentum" value={`${(market.momentum * 100).toFixed(0)}%`} />
        <MetricMini label="RSI" value={market.rsi.toString()} />
        <MetricMini label="24h" value={`${isPositive ? '+' : ''}${market.change24h.toFixed(1)}%`} positive={isPositive} />
      </div>

      <div className="h-2 bg-synchro-border rounded-full overflow-hidden">
        <div 
          className="h-full bg-synchro-navy rounded-full transition-all duration-500" 
          style={{ width: `${Math.min(100, Math.max(0, market.momentum * 100))}%` }}
        />
      </div>
    </div>
  );
}

function MetricMini({ label, value, positive }: { label: string; value: string; positive?: boolean }) {
  return (
    <div className="text-center p-2 bg-synchro-border/50 rounded-xl">
      <p className="text-[11px] font-medium text-synchro-text-secondary uppercase tracking-wider">{label}</p>
      <p className={cn(
        'text-sm font-bold mt-1',
        positive ? 'text-green-600' : positive === false ? 'text-red-600' : 'text-synchro-text-primary'
      )}>{value}</p>
    </div>
  );
}