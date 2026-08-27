export type MarketRegime = 'trend_up' | 'trend_down' | 'range' | 'high_vol' | 'crisis';
export type TradeDirection = 'buy' | 'sell';
export type TradeStatus = 'open' | 'breakeven' | 'trailing' | 'closed';
export type SignalDecision = 'BUY' | 'SELL' | 'WAIT';
export type ApprovalStatus = 'pending' | 'approved' | 'declined' | 'timeout';

export interface User {
  id: string;
  email: string;
  name: string;
  telegramChatId?: string;
  isActive: boolean;
}

export interface Account {
  id: string;
  userId: string;
  name: string;
  allocatedCapital: number;
  activeMarkets: string[];
  riskPhase: number;
  minScore: number;
  isActive: boolean;
  isDemo: boolean;
}

export interface Trade {
  id: string;
  accountId: string;
  symbol: string;
  direction: TradeDirection;
  entryPrice: number;
  exitPrice?: number;
  slInitial: number;
  slCurrent?: number;
  tp: number;
  lots: number;
  pnl?: number;
  status: TradeStatus;
  scoreComponents: ScoreComponents;
  filtersSnapshot: Record<string, boolean>;
  openedAt: string;
  closedAt?: string;
}

export interface ScoreComponents {
  regime: number;
  trend: number;
  momentum: number;
  structure: number;
  trigger: number;
  total: number;
}

export interface Signal {
  id: string;
  accountId: string;
  symbol: string;
  timestamp: string;
  apexLayerResults: ApexLayerResults;
  decision: SignalDecision;
  reasonText: string;
}

export interface ApexLayerResults {
  regime: LayerResult;
  trend: LayerResult;
  momentum: LayerResult;
  structure: LayerResult;
  trigger: LayerResult;
}

export interface LayerResult {
  passed: boolean;
  score: number;
  details: string;
}

export interface EquitySnapshot {
  accountId: string;
  timestamp: string;
  balance: number;
  equity: number;
  dailyPnl: number;
}

export interface Pattern {
  id: string;
  tradeId: string;
  features: Record<string, any>;
  hmmState?: string;
  session?: string;
  outcome: 'win' | 'loss' | 'breakeven';
  isWin: boolean;
}

export interface EvolutionLog {
  id: string;
  cycleDate: string;
  variationsTested: number;
  winner?: Record<string, any>;
  improvementPct?: number;
  demoValidated: boolean;
  humanApproved: boolean;
  createdAt: string;
}

export interface ModelVersion {
  id: string;
  version: string;
  params: Record<string, any>;
  backtestMetrics: BacktestMetrics;
  deployedAt: string;
  rolledBack: boolean;
}

export interface BacktestMetrics {
  totalTrades: number;
  winRate: number;
  profitFactor: number;
  maxDrawdown: number;
  sharpePerTrade: number;
  returnPct: number;
  finalBalance: number;
}

export interface ApprovalRequest {
  id: string;
  type: 'evolution' | 'trade_override' | 'risk_change';
  title: string;
  details: Record<string, string>;
  createdAt: string;
  expiresAt: string;
  status: ApprovalStatus;
  decidedAt?: string;
  approved?: boolean;
}

export interface MarketData {
  symbol: string;
  regime: MarketRegime;
  trend: 'bullish' | 'bearish' | 'neutral';
  momentum: number;
  rsi: number;
  price: number;
  change24h: number;
}

export interface Candle {
  epoch: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface Insight {
  id: string;
  type: 'best_hour' | 'worst_hour' | 'best_symbol' | 'worst_symbol' | 'pattern' | 'risk';
  title: string;
  description: string;
  value: string;
  confidence: number;
}