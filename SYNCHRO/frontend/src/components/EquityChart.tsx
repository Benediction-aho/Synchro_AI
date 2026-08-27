import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface EquityChartProps {
  data: Array<{ timestamp: string; equity: number; balance: number }>;
  initialCapital: number;
}

export function EquityChart({ data, initialCapital }: EquityChartProps) {
  if (!data.length) {
    return (
      <div className="h-64 flex items-center justify-center bg-synchro-border/50 rounded-xl">
        <p className="text-synchro-text-secondary">No equity data available yet</p>
      </div>
    );
  }

  const chartData = [...data].reverse().map((point, index) => ({
    ...point,
    pnl: point.equity - initialCapital,
    pnlPct: initialCapital > 0 ? ((point.equity - initialCapital) / initialCapital) * 100 : 0,
    name: index.toString(),
  }));

  const maxEquity = Math.max(...chartData.map(d => d.equity));
  const minEquity = Math.min(...chartData.map(d => d.equity));
  const range = maxEquity - minEquity || initialCapital * 0.1;

  return (
    <div className="h-64" style={{ width: '100%' }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#BABAF3" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#BABAF3" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#D0D0E8" vertical={false} />
          <XAxis 
            dataKey="name" 
            hide 
            tick={{ fill: '#474747', fontSize: 11 }}
          />
          <YAxis 
            hide 
            domain={[minEquity - range * 0.1, maxEquity + range * 0.1]}
            tick={{ fill: '#474747', fontSize: 11 }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #D0D0E8',
              borderRadius: '12px',
              boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
              padding: '12px',
            }}
          />
          <Line
            type="monotone"
            dataKey="equity"
            stroke="#1A3A5C"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 6, fill: '#1A3A5C', strokeWidth: 2 }}
          />
          <Line
            type="monotone"
            dataKey="equity"
            stroke="url(#equityGradient)"
            strokeWidth={0}
            fillOpacity={1}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}