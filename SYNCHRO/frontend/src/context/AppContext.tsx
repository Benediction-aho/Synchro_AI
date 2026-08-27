import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import type { User, Account, Trade, Signal, EquitySnapshot, MarketData, ApprovalRequest } from '../types';

interface AppState {
  user: User | null;
  accounts: Account[];
  activeAccount: Account | null;
  trades: Trade[];
  signals: Signal[];
  equityHistory: EquitySnapshot[];
  marketData: MarketData[];
  approvals: ApprovalRequest[];
  isLoading: boolean;
  explainMode: boolean;
  killSwitchActive: boolean;
  
  // Actions
  setUser: (user: User | null) => void;
  setAccounts: (accounts: Account[]) => void;
  setActiveAccount: (account: Account | null) => void;
  addTrade: (trade: Trade) => void;
  updateTrade: (trade: Trade) => void;
  addSignal: (signal: Signal) => void;
  addEquitySnapshot: (snapshot: EquitySnapshot) => void;
  setMarketData: (data: MarketData[]) => void;
  addApproval: (approval: ApprovalRequest) => void;
  updateApproval: (id: string, updates: Partial<ApprovalRequest>) => void;
  setExplainMode: (enabled: boolean) => void;
  setKillSwitch: (active: boolean) => void;
  setLoading: (loading: boolean) => void;
}

const initialState: AppState = {
  user: null,
  accounts: [],
  activeAccount: null,
  trades: [],
  signals: [],
  equityHistory: [],
  marketData: [],
  approvals: [],
  isLoading: false,
  explainMode: false,
  killSwitchActive: false,
  
  setUser: () => {},
  setAccounts: () => {},
  setActiveAccount: () => {},
  addTrade: () => {},
  updateTrade: () => {},
  addSignal: () => {},
  addEquitySnapshot: () => {},
  setMarketData: () => {},
  addApproval: () => {},
  updateApproval: () => {},
  setExplainMode: () => {},
  setKillSwitch: () => {},
  setLoading: () => {},
};

const AppContext = createContext<AppState>(initialState);

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AppState>({
    ...initialState,
    user: {
      id: '1',
      email: 'trader@example.com',
      name: 'Alex Trader',
      telegramChatId: '123456789',
      isActive: true,
    },
    accounts: [
      {
        id: 'acc-1',
        userId: '1',
        name: 'Main Account',
        allocatedCapital: 10000,
        activeMarkets: ['R_75', 'R_100', 'frxEURUSD'],
        riskPhase: 2,
        minScore: 5,
        isActive: true,
        isDemo: true,
      },
    ],
    activeAccount: {
      id: 'acc-1',
      userId: '1',
      name: 'Main Account',
      allocatedCapital: 10000,
      activeMarkets: ['R_75', 'R_100', 'frxEURUSD'],
      riskPhase: 2,
      minScore: 5,
      isActive: true,
      isDemo: true,
    },
    trades: [],
    signals: [],
    equityHistory: [],
    marketData: [],
    approvals: [],
    isLoading: false,
    explainMode: false,
    killSwitchActive: false,
  });

  const setUser = useCallback((user: User | null) => setState(s => ({ ...s, user })), []);
  const setAccounts = useCallback((accounts: Account[]) => setState(s => ({ ...s, accounts })), []);
  const setActiveAccount = useCallback((account: Account | null) => setState(s => ({ ...s, activeAccount: account })), []);
  
  const addTrade = useCallback((trade: Trade) => setState(s => ({ 
    ...s, 
    trades: [trade, ...s.trades].slice(0, 100) 
  })), []);
  
  const updateTrade = useCallback((trade: Trade) => setState(s => ({ 
    ...s, 
    trades: s.trades.map(t => t.id === trade.id ? trade : t) 
  })), []);
  
  const addSignal = useCallback((signal: Signal) => setState(s => ({ 
    ...s, 
    signals: [signal, ...s.signals].slice(0, 100) 
  })), []);
  
  const addEquitySnapshot = useCallback((snapshot: EquitySnapshot) => setState(s => ({ 
    ...s, 
    equityHistory: [snapshot, ...s.equityHistory].slice(0, 500) 
  })), []);
  
  const setMarketData = useCallback((data: MarketData[]) => setState(s => ({ ...s, marketData: data })), []);
  
  const addApproval = useCallback((approval: ApprovalRequest) => setState(s => ({ 
    ...s, 
    approvals: [approval, ...s.approvals] 
  })), []);
  
  const updateApproval = useCallback((id: string, updates: Partial<ApprovalRequest>) => setState(s => ({ 
    ...s, 
    approvals: s.approvals.map(a => a.id === id ? { ...a, ...updates } : a) 
  })), []);
  
  const setExplainMode = useCallback((enabled: boolean) => setState(s => ({ ...s, explainMode: enabled })), []);
  const setKillSwitch = useCallback((active: boolean) => setState(s => ({ ...s, killSwitchActive: active })), []);
  const setLoading = useCallback((loading: boolean) => setState(s => ({ ...s, isLoading: loading })), []);

  const value: AppState = {
    ...state,
    setUser,
    setAccounts,
    setActiveAccount,
    addTrade,
    updateTrade,
    addSignal,
    addEquitySnapshot,
    setMarketData,
    addApproval,
    updateApproval,
    setExplainMode,
    setKillSwitch,
    setLoading,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}