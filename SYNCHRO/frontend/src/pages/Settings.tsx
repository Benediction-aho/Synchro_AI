import { useApp } from '../context/AppContext';
import { cn } from '../utils/cn';
import { 
  Shield, 
  Bell, 
  Globe, 
  Save, 
  Loader2,
  MessageSquare,
  DollarSign,
  Zap
} from 'lucide-react';
import { useState } from 'react';

export function Settings() {
  const { activeAccount, user, killSwitchActive, setKillSwitch } = useApp();
  const [activeTab, setActiveTab] = useState<'capital' | 'markets' | 'telegram' | 'security' | 'notifications'>('capital');
  const [saving, setSaving] = useState(false);

  const capital = activeAccount?.allocatedCapital || 10000;
  const [capitalInput, setCapitalInput] = useState(capital.toString());
  
  const markets = activeAccount?.activeMarkets || ['R_75', 'R_100', 'frxEURUSD'];
  const [selectedMarkets, setSelectedMarkets] = useState<string[]>(markets);
  const availableMarkets = ['R_75', 'R_100', 'R_50', 'R_25', 'R_10', 'frxEURUSD', 'frxGBPUSD', 'frxUSDJPY', 'frxAUDUSD', 'frxUSDCAD'];

  const [telegramLinked, setTelegramLinked] = useState(!!user?.telegramChatId);
  const [telegramChatId] = useState(user?.telegramChatId || '');
  
  const [notifications, setNotifications] = useState({
    tradeExecution: true,
    approvalRequests: true,
    crisisAlerts: true,
    dailySummary: false,
    weeklyReport: true,
  });

  const handleSave = async (_section: string) => {
    setSaving(true);
    await new Promise(r => setTimeout(r, 1000));
    setSaving(false);
    // In real app: call API to save
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-synchro-text-primary">Settings</h1>
        <p className="text-synchro-text-secondary">Configure capital, markets, notifications, and security</p>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 bg-synchro-border rounded-xl p-1" role="tablist">
        {[
          { id: 'capital', label: 'Capital', icon: DollarSign },
          { id: 'markets', label: 'Markets', icon: Globe },
          { id: 'telegram', label: 'Telegram', icon: MessageSquare },
          { id: 'security', label: 'Security', icon: Shield },
          { id: 'notifications', label: 'Notifications', icon: Bell },
        ].map(tab => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={cn(
              'flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-all',
              activeTab === tab.id 
                ? 'bg-white text-synchro-navy shadow-sm' 
                : 'text-synchro-text-secondary hover:text-synchro-text-primary'
            )}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Panels */}
      <div className="synchro-card animate-fade-in">
        {activeTab === 'capital' && <CapitalSettings 
          capital={capital} 
          capitalInput={capitalInput} 
          setCapitalInput={setCapitalInput} 
          saving={saving} 
          onSave={handleSave} 
        />}
        {activeTab === 'markets' && <MarketsSettings 
          selectedMarkets={selectedMarkets} 
          setSelectedMarkets={setSelectedMarkets} 
          availableMarkets={availableMarkets} 
          saving={saving} 
          onSave={handleSave} 
        />}
        {activeTab === 'telegram' && <TelegramSettings 
          telegramLinked={telegramLinked} 
          setTelegramLinked={setTelegramLinked} 
          telegramChatId={telegramChatId} 
          user={user} 
        />}
        {activeTab === 'security' && <SecuritySettings 
          killSwitchActive={killSwitchActive} 
          setKillSwitch={setKillSwitch} 
        />}
        {activeTab === 'notifications' && <NotificationsSettings 
          notifications={notifications} 
          setNotifications={setNotifications} 
        />}
      </div>

      {/* Locked Settings Notice */}
      <div className="synchro-card p-4 bg-amber-50 border-amber-200">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center">
            <Zap className="w-5 h-5 text-amber-600" />
          </div>
          <div>
            <h4 className="font-semibold text-amber-800">Non-Negotiable Settings (Locked)</h4>
            <p className="text-sm text-amber-700 mt-1">
              These protect your capital and cannot be changed:
            </p>
            <ul className="text-sm text-amber-700 mt-2 space-y-1 list-disc list-inside">
              <li>Minimum Score: <strong>5/5</strong> — only perfect setups trade</li>
              <li>Max Risk per Trade: <strong>1.5%</strong> — hard cap</li>
              <li>Stop Loss: <strong>Mandatory</strong> — every trade</li>
              <li>Breakeven: <strong>Auto at +10 pips</strong> — no exceptions</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

function CapitalSettings({ capital, capitalInput, setCapitalInput, saving, onSave }: any) {
  return (
    <div className="p-6 space-y-6 max-w-xl">
      <div>
        <h3 className="text-lg font-semibold text-synchro-text-primary mb-2">Allocated Capital</h3>
        <p className="text-sm text-synchro-text-secondary">
          The amount SYNCHRO can trade with. Adjust based on your risk tolerance.
        </p>
      </div>

      <div className="synchro-card p-4">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-xl bg-green-100 flex items-center justify-center">
            <DollarSign className="w-8 h-8 text-green-600" />
          </div>
          <div>
            <p className="text-sm text-synchro-text-secondary">Current Allocation</p>
            <p className="text-3xl font-bold text-synchro-text-primary">${capital.toLocaleString()}</p>
          </div>
        </div>
      </div>

      <div>
        <label className="synchro-label">New Capital Amount (USD)</label>
        <div className="relative">
          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-synchro-text-secondary">$</span>
          <input
            type="number"
            min="100"
            max="1000000"
            step="100"
            value={capitalInput}
            onChange={(e) => setCapitalInput(e.target.value)}
            className="synchro-input pl-10"
          />
        </div>
        <p className="text-xs text-synchro-text-secondary mt-2">
          Minimum $100 • Changes take effect next trading session
        </p>
      </div>

      <div className="flex justify-end">
        <button 
          onClick={() => onSave('capital')} 
          disabled={saving}
          className="synchro-btn-primary"
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
          Save Capital
        </button>
      </div>
    </div>
  );
}

function MarketsSettings({ 
  selectedMarkets, 
  setSelectedMarkets, 
  availableMarkets, 
  saving, 
  onSave 
}: { 
  selectedMarkets: string[];
  setSelectedMarkets: (markets: string[] | ((prev: string[]) => string[])) => void;
  availableMarkets: string[];
  saving: boolean;
  onSave: (section: string) => void;
}) {
  const toggleMarket = (market: string) => {
    setSelectedMarkets((prev: string[]) => 
      prev.includes(market) ? prev.filter((m: string) => m !== market) : [...prev, market]
    );
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-synchro-text-primary mb-2">Active Markets</h3>
        <p className="text-sm text-synchro-text-secondary">
          Select which symbols SYNCHRO can trade. Minimum 1, maximum 10.
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        {availableMarkets.map(market => {
          const isSelected = selectedMarkets.includes(market);
          const isSynthetic = market.startsWith('R_');
          return (
            <button
              key={market}
              onClick={() => toggleMarket(market)}
              className={cn(
                'p-4 rounded-xl border-2 text-center transition-all duration-200 flex flex-col items-center gap-2',
                isSelected 
                  ? 'border-synchro-navy bg-synchro-navy/5' 
                  : 'border-synchro-border hover:border-synchro-navy'
              )}
            >
              <span className={cn('font-medium', isSelected ? 'text-synchro-navy' : 'text-synchro-text-primary')}>
                {market}
              </span>
              <span className={cn(
                'text-xs px-2 py-0.5 rounded-full',
                isSynthetic 
                  ? 'bg-purple-100 text-purple-700' 
                  : 'bg-blue-100 text-blue-700'
              )}>
                {isSelected ? 'Active' : 'Inactive'}
              </span>
            </button>
          );
        })}
      </div>

      <div className="flex justify-end pt-4 border-t border-synchro-border">
        <button 
          onClick={() => onSave('markets')} 
          disabled={saving}
          className="synchro-btn-primary"
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
          Save Markets
        </button>
      </div>
    </div>
  );
}

function TelegramSettings({ 
  telegramLinked, 
  setTelegramLinked, 
  telegramChatId, 
  user
}: { 
  telegramLinked: boolean;
  setTelegramLinked: (linked: boolean) => void;
  telegramChatId: string;
  user: any;
}) {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-synchro-text-primary mb-2">Telegram Integration</h3>
        <p className="text-sm text-synchro-text-secondary">
          Link your Telegram to receive approvals, trade alerts, and crisis broadcasts.
        </p>
      </div>

      <div className="synchro-card p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center">
              <MessageSquare className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <p className="font-semibold text-synchro-text-primary">Telegram Bot</p>
              <p className="text-sm text-synchro-text-secondary">
                {telegramLinked ? `Linked: ${telegramChatId}` : 'Not connected'}
              </p>
            </div>
          </div>
          <button
            onClick={() => setTelegramLinked(!telegramLinked)}
            className={cn(
              'px-4 py-2 rounded-xl font-medium transition-all',
              telegramLinked ? 'synchro-btn-secondary' : 'synchro-btn-primary'
            )}
          >
            {telegramLinked ? 'Unlink' : 'Link Telegram'}
          </button>
        </div>
      </div>

      {telegramLinked && (
        <div className="space-y-4">
          <h4 className="font-medium text-synchro-text-primary">Test Notifications</h4>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: 'Test Approval Card', desc: 'Receive a sample approval request' },
              { label: 'Test Trade Alert', desc: 'Receive a sample trade notification' },
              { label: 'Test Crisis Broadcast', desc: 'Receive a sample crisis alert' },
            ].map((test, i) => (
              <button key={i} className="synchro-btn-secondary px-4 py-3 text-left">
                <div className="font-medium">{test.label}</div>
                <div className="text-xs text-synchro-text-secondary">{test.desc}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      {!telegramLinked && (
        <div className="synchro-card p-4 bg-blue-50 border-blue-200">
          <h4 className="font-semibold text-blue-800 mb-2">How to Link Telegram</h4>
          <ol className="text-sm text-blue-700 space-y-2 list-decimal list-inside">
            <li>Open Telegram and search for <strong>@SYNCHRO_Bot</strong></li>
            <li>Send <code className="bg-white/50 px-1 rounded">/start</code></li>
            <li>Send <code className="bg-white/50 px-1 rounded">/link {user?.email || 'your-email@example.com'}</code></li>
            <li>Bot will confirm linking — you're ready!</li>
          </ol>
        </div>
      )}
    </div>
  );
}

function SecuritySettings({ killSwitchActive, setKillSwitch }: any) {
  return (
    <div className="p-6 space-y-6 max-w-xl">
      <div>
        <h3 className="text-lg font-semibold text-synchro-text-primary mb-2">Kill Switch</h3>
        <p className="text-sm text-synchro-text-secondary">
          Emergency halt — stops ALL trading instantly. Use only in extreme situations.
        </p>
      </div>

      <div className="synchro-card p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="font-semibold text-synchro-text-primary">Kill Switch Status</p>
            <p className="text-sm text-synchro-text-secondary">
              {killSwitchActive ? 'ACTIVE — All trading halted' : 'Inactive — Trading enabled'}
            </p>
          </div>
          <div className="relative">
            <input
              type="checkbox"
              checked={killSwitchActive}
              onChange={(e) => setKillSwitch(e.target.checked)}
              className="peer w-14 h-8 rounded-full bg-synchro-border peer-checked:bg-red-600 appearance-none cursor-pointer after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:w-5 after:h-5 after:bg-white after:rounded-full after:transition-all peer-checked:after:translate-x-full"
            />
          </div>
        </div>

        {killSwitchActive && (
          <div className="p-4 bg-red-50 rounded-xl border border-red-200">
            <div className="flex items-center gap-3 text-red-700">
              <Shield className="w-5 h-5" />
              <div>
                <p className="font-semibold">KILL SWITCH ACTIVE</p>
                <p className="text-sm">No new positions will be opened. Existing positions may still close on SL/TP.</p>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="synchro-card p-6">
        <h4 className="font-semibold text-synchro-text-primary mb-4">API Security</h4>
        <div className="space-y-4">
          <SecurityItem 
            label="API Credentials" 
            desc="Deriv API tokens are encrypted with AES-GCM" 
            status="secured" 
          />
          <SecurityItem 
            label="Two-Factor Auth" 
            desc="Not yet configured — recommended for live accounts" 
            status="warning" 
            action="Enable 2FA"
          />
          <SecurityItem 
            label="Session Timeout" 
            desc="Auto-logout after 30 minutes of inactivity" 
            status="secured" 
          />
        </div>
      </div>
    </div>
  );
}

function SecurityItem({ label, desc, status, action }: { label: string; desc: string; status: 'secured' | 'warning'; action?: string }) {
  return (
    <div className="flex items-center justify-between p-4 bg-synchro-border/50 rounded-xl">
      <div>
        <p className="font-medium text-synchro-text-primary">{label}</p>
        <p className="text-sm text-synchro-text-secondary">{desc}</p>
      </div>
      <div className="flex items-center gap-3">
        <span className={cn(
          'inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium',
          status === 'secured' ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'
        )}>
          {status === 'secured' ? '✅ Secured' : '⚠️ Action Needed'}
        </span>
        {action && <button className="synchro-btn-secondary text-sm px-3 py-1.5">{action}</button>}
      </div>
    </div>
  );
}

function NotificationsSettings({ notifications, setNotifications }: any) {
  const notificationTypes = [
    { key: 'tradeExecution', label: 'Trade Execution', desc: 'Real-time alerts when trades open/close', icon: Zap },
    { key: 'approvalRequests', label: 'Approval Requests', desc: '15-min approval cards for evolution/trade overrides', icon: MessageSquare },
    { key: 'crisisAlerts', label: 'Crisis Broadcasts', desc: 'Immediate alerts for regime changes or kill switch', icon: Shield },
    { key: 'dailySummary', label: 'Daily Summary', desc: 'End-of-day P&L and trade recap', icon: DollarSign },
    { key: 'weeklyReport', label: 'Weekly Report', desc: 'Comprehensive weekly performance report', icon: Shield },
  ];

  return (
    <div className="p-6 space-y-4">
      <div>
        <h3 className="text-lg font-semibold text-synchro-text-primary mb-2">Notification Preferences</h3>
        <p className="text-sm text-synchro-text-secondary">
          Choose what alerts you receive via Telegram and in-app
        </p>
      </div>

      <div className="space-y-3">
        {notificationTypes.map(({ key, label, desc, icon: Icon }) => (
          <div key={key} className="synchro-card p-4 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl bg-synchro-card flex items-center justify-center">
                <Icon className="w-5 h-5 text-synchro-text-primary" />
              </div>
              <div>
                <p className="font-medium text-synchro-text-primary">{label}</p>
                <p className="text-sm text-synchro-text-secondary">{desc}</p>
              </div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={notifications[key]}
                onChange={(e) => setNotifications({ ...notifications, [key]: e.target.checked })}
                className="peer w-10 h-6 rounded-full bg-synchro-border peer-checked:bg-synchro-navy appearance-none cursor-pointer after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:w-5 after:h-5 after:bg-white after:rounded-full after:transition-all peer-checked:after:translate-x-full"
              />
            </label>
          </div>
        ))}
      </div>
    </div>
  );
}