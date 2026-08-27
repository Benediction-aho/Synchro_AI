import type { Candle } from '../types';

interface CandlestickChartProps {
  symbol: string;
  showSignals: boolean;
  regime: string;
}

const regimeColors = {
  trend_up: { bull: '#10B981', bear: '#EF4444' },
  trend_down: { bull: '#10B981', bear: '#EF4444' },
  range: { bull: '#3B82F6', bear: '#3B82F6' },
  high_vol: { bull: '#8B5CF6', bear: '#8B5CF6' },
  crisis: { bull: '#EF4444', bear: '#EF4444' },
};

function generateMockCandles(symbol: string, count: number = 100): Candle[] {
  const candles: Candle[] = [];
  let price = symbol.startsWith('frx') ? 1.08 : 18000;
  const volatility = symbol.startsWith('frx') ? 0.0008 : 15;
  
  for (let i = count - 1; i >= 0; i--) {
    const drift = (Math.random() - 0.5) * volatility * 0.5;
    const open = price;
    const close = price + drift + (Math.random() - 0.5) * volatility;
    const high = Math.max(open, close) + Math.random() * volatility * 0.5;
    const low = Math.min(open, close) - Math.random() * volatility * 0.5;
    
    candles.push({
      epoch: Date.now() - i * 60000,
      open,
      high,
      low,
      close,
    });
    price = close;
  }
  return candles;
}

function generateSignals(candles: Candle[], _regime: string): Array<{index: number, type: 'buy' | 'sell' | 'wait', price: number}> {
  const signals: Array<{index: number, type: 'buy' | 'sell' | 'wait', price: number}> = [];
  
  for (let i = 10; i < candles.length; i += 15 + Math.floor(Math.random() * 10)) {
    const rand = Math.random();
    if (rand < 0.35) {
      signals.push({ index: i, type: 'buy', price: candles[i].low * 0.9995 });
    } else if (rand < 0.65) {
      signals.push({ index: i, type: 'sell', price: candles[i].high * 1.0005 });
    } else {
      signals.push({ index: i, type: 'wait', price: candles[i].close });
    }
  }
  return signals;
}

export function CandlestickChart({ symbol, showSignals, regime }: CandlestickChartProps) {
  const candles = generateMockCandles(symbol, 100);
  const signals = generateSignals(candles, regime);
  const colors = regimeColors[regime as keyof typeof regimeColors] || regimeColors.trend_up;

  const chartData = candles.map((c, i) => ({
    ...c,
    name: new Date(c.epoch).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    signal: signals.find(s => s.index === i),
  }));

  const maxPrice = Math.max(...candles.map(c => c.high));
  const minPrice = Math.min(...candles.map(c => c.low));
  const priceRange = maxPrice - minPrice || 1;

  // SVG dimensions
  const width = 800;
  const height = 400;
  const padding = { top: 20, right: 60, bottom: 20, left: 0 };
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;

  const xScale = (index: number) => padding.left + (index / (chartData.length - 1)) * innerWidth;
  const yScale = (price: number) => padding.top + innerHeight - ((price - minPrice) / priceRange) * innerHeight;

  return (
    <div style={{ width: '100%', height: '100%', overflow: 'hidden' }}>
      <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet" style={{ width: '100%', height: '100%' }}>
        <defs>
          <linearGradient id="volumeGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#BABAF3" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#BABAF3" stopOpacity="0" />
          </linearGradient>
        </defs>
        
        {/* Grid */}
        <g stroke="#D0D0E8" strokeDasharray="3 3" strokeWidth="0.5">
          {/* Horizontal grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map(ratio => (
            <line 
              key={ratio}
              x1={padding.left} 
              y1={padding.top + innerHeight * ratio} 
              x2={width - padding.right} 
              y2={padding.top + innerHeight * ratio} 
            />
          ))}
        </g>

        {/* Current price line */}
        <line
          x1={padding.left}
          y1={yScale(chartData[chartData.length - 1].close)}
          x2={width - padding.right}
          y2={yScale(chartData[chartData.length - 1].close)}
          stroke="#C8960C"
          strokeDasharray="5 5"
          strokeWidth="1"
        />
        
        {/* Current price label */}
        <text
          x={width - padding.right + 5}
          y={yScale(chartData[chartData.length - 1].close) - 4}
          fontSize="10"
          fill="#C8960C"
          fontWeight="bold"
        >
          Current: {chartData[chartData.length - 1].close.toLocaleString(undefined, { minimumFractionDigits: symbol.startsWith('frx') ? 4 : 2 })}
        </text>

        {/* Candlesticks */}
        <g>
          {chartData.map((candle, index) => {
            const isBullish = candle.close >= candle.open;
            const color = isBullish ? colors.bull : colors.bear;
            const x = xScale(index);
            const openY = yScale(candle.open);
            const closeY = yScale(candle.close);
            const highY = yScale(candle.high);
            const lowY = yScale(candle.low);
            const bodyHeight = Math.max(Math.abs(openY - closeY), 1);
            const bodyY = Math.min(openY, closeY);

            return (
              <g key={index}>
                {/* Wick */}
                <line
                  x1={x}
                  x2={x}
                  y1={highY}
                  y2={lowY}
                  stroke={color}
                  strokeWidth={1}
                />
                {/* Body */}
                <rect
                  x={x - 4}
                  y={bodyY}
                  width={8}
                  height={bodyHeight}
                  fill={color}
                  stroke={color}
                  strokeWidth={1}
                />
              </g>
            );
          })}
        </g>

        {/* APEX Signals */}
        {showSignals && (
          <g>
            {chartData.map((candle, index) => {
              if (!candle.signal) return null;
              
              const signal = candle.signal;
              const isBuy = signal.type === 'buy';
              const isSell = signal.type === 'sell';
              const isWait = signal.type === 'wait';
              const signalX = xScale(index);
              const signalY = yScale(signal.price);

              return (
                <g key={index}>
                  {isBuy && (
                    <>
                      <polygon
                        points={`${signalX - 6},${signalY} ${signalX},${signalY - 8} ${signalX + 6},${signalY}`}
                        fill="#10B981"
                      />
                      <text
                        x={signalX + 10}
                        y={signalY - 4}
                        fontSize="10"
                        fill="#10B981"
                        fontWeight="bold"
                      >
                        BUY
                      </text>
                    </>
                  )}
                  {isSell && (
                    <>
                      <polygon
                        points={`${signalX - 6},${signalY} ${signalX},${signalY + 8} ${signalX + 6},${signalY}`}
                        fill="#EF4444"
                      />
                      <text
                        x={signalX + 10}
                        y={signalY + 14}
                        fontSize="10"
                        fill="#EF4444"
                        fontWeight="bold"
                      >
                        SELL
                      </text>
                    </>
                  )}
                  {isWait && (
                    <circle
                      cx={signalX}
                      cy={signalY}
                      r={4}
                      fill="#9CA3AF"
                      stroke="#6B7280"
                      strokeWidth={1}
                    />
                  )}
                </g>
              );
            })}
          </g>
        )}
      </svg>
    </div>
  );
}