import { useApp } from '../context/AppContext';
import { cn } from '../utils/cn';
import { Zap, MessageSquare, CheckCircle2, Key, DollarSign, Globe } from 'lucide-react';
import { useState } from 'react';

const steps = [
  {
    id: 1,
    title: 'Connect Account',
    desc: 'Paste your Deriv API token to link your trading account',
    icon: Key,
    fields: ['apiToken'],
  },
  {
    id: 2,
    title: 'Set Capital',
    desc: 'Choose how much capital SYNCHRO can trade with',
    icon: DollarSign,
    fields: ['capital'],
  },
  {
    id: 3,
    title: 'Select Markets',
    desc: 'Pick which symbols SYNCHRO can trade',
    icon: Globe,
    fields: ['markets'],
  },
  {
    id: 4,
    title: 'Link Telegram',
    desc: 'Get approvals, alerts, and crisis broadcasts',
    icon: MessageSquare,
    fields: ['telegram'],
  },
];

export function Onboarding() {
  const { activeAccount } = useApp();
  const [currentStep, setCurrentStep] = useState(1);
  const [apiToken, setApiToken] = useState('');
  const [capital, setCapital] = useState(activeAccount?.allocatedCapital || 10000);
  const [selectedMarkets, setSelectedMarkets] = useState(activeAccount?.activeMarkets || ['R_75', 'R_100', 'frxEURUSD']);
  const [telegramLinked, setTelegramLinked] = useState(false);
  const availableMarkets = ['R_75', 'R_100', 'R_50', 'R_25', 'R_10', 'frxEURUSD', 'frxGBPUSD', 'frxUSDJPY', 'frxAUDUSD', 'frxUSDCAD'];

  const handleNext = () => {
    if (currentStep < steps.length) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleComplete = () => {
    // In real app: call API to save settings
    alert('Onboarding complete! SYNCHRO is ready to trade.');
  };

  const step = steps[currentStep - 1];
  const progress = (currentStep / steps.length) * 100;

  const toggleMarket = (market: string) => {
    setSelectedMarkets(prev => 
      prev.includes(market) ? prev.filter(m => m !== market) : [...prev, market]
    );
  };

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      {/* Progress Bar */}
      <div className="synchro-card p-6">
        <div className="flex items-center justify-between mb-6">
          {steps.map((s, i) => (
            <div key={s.id} className="flex flex-col items-center flex-1 relative">
              <div className={cn(
                'w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold transition-all duration-300 relative z-10',
                i + 1 < currentStep 
                  ? 'bg-synchro-navy text-white' 
                  : i + 1 === currentStep 
                    ? 'bg-synchro-gold text-white shadow-lg shadow-amber-300/50 ring-4 ring-amber-100' 
                    : 'bg-synchro-border text-synchro-text-secondary'
              )}>
                {i + 1 < currentStep ? <CheckCircle2 className="w-5 h-5" /> : i + 1}
              </div>
              <span className="mt-2 text-xs text-center text-synchro-text-secondary">{s.title}</span>
              {i < steps.length - 1 && (
                <div className={cn(
                  'absolute top-5 left-1/2 w-full h-1 -translate-x-1/2',
                  i + 1 < currentStep ? 'bg-synchro-navy' : 'bg-synchro-border'
                )} />
              )}
            </div>
          ))}
        </div>
        <div className="h-2 bg-synchro-border rounded-full overflow-hidden">
          <div 
            className="h-full bg-synchro-gold rounded-full transition-all duration-500" 
            style={{ width: `${progress}%` }} 
          />
        </div>
        <p className="text-center text-sm text-synchro-text-secondary mt-4">
          Step {currentStep} of {steps.length}
        </p>
      </div>

      {/* Step Content */}
      <div className="synchro-card p-6 animate-slide-up">
        <div className="flex items-center gap-4 mb-6">
          <div className={cn('w-12 h-12 rounded-xl flex items-center justify-center', 
            currentStep === 1 ? 'bg-blue-100 text-blue-600' :
            currentStep === 2 ? 'bg-green-100 text-green-600' :
            currentStep === 3 ? 'bg-purple-100 text-purple-600' :
            'bg-blue-100 text-blue-600'
          )}>
            <step.icon className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-synchro-text-primary">{step.title}</h2>
            <p className="text-synchro-text-secondary">{step.desc}</p>
          </div>
        </div>

        {currentStep === 1 && (
          <div className="space-y-4">
            <label className="synchro-label">Deriv API Token</label>
            <div className="relative">
              <input
                type="password"
                value={apiToken}
                onChange={(e) => setApiToken(e.target.value)}
                placeholder="Paste your Deriv API token here"
                className="synchro-input pr-10"
              />
              <button className="absolute right-3 top-1/2 -translate-y-1/2 text-synchro-text-secondary hover:text-synchro-text-primary">
                👁
              </button>
            </div>
            <p className="text-xs text-synchro-text-secondary">
              Get your token from <a href="https://app.deriv.com/account/api-token" target="_blank" rel="noopener" className="text-synchro-navy underline">Deriv App</a>
            </p>
          </div>
        )}

        {currentStep === 2 && (
          <div className="space-y-4">
            <label className="synchro-label">Allocated Capital (USD)</label>
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-synchro-text-secondary">$</span>
              <input
                type="number"
                min="100"
                max="1000000"
                step="100"
                value={capital}
                onChange={(e) => setCapital(parseInt(e.target.value) || 0)}
                className="synchro-input pl-10"
              />
            </div>
            <p className="text-xs text-synchro-text-secondary">Minimum $100</p>
          </div>
        )}

        {currentStep === 3 && (
          <div className="space-y-4">
            <label className="synchro-label">Active Markets ({selectedMarkets.length} selected)</label>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {availableMarkets.map(market => {
                const isSelected = selectedMarkets.includes(market);
                const isSynthetic = market.startsWith('R_');
                return (
                  <button
                    key={market}
                    type="button"
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
            <p className="text-xs text-synchro-text-secondary">Minimum 1, maximum 10</p>
          </div>
        )}

        {currentStep === 4 && (
          <div className="space-y-4">
            <div className="synchro-card p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center">
                    <MessageSquare className="w-6 h-6 text-blue-600" />
                  </div>
                  <div>
                    <p className="font-semibold text-synchro-text-primary">Telegram Bot</p>
                    <p className="text-sm text-synchro-text-secondary">
                      {telegramLinked ? 'Linked ✓' : 'Not connected'}
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

            {!telegramLinked && (
              <div className="synchro-card p-4 bg-blue-50 border-blue-200">
                <h4 className="font-semibold text-blue-800 mb-2">How to Link Telegram</h4>
                <ol className="text-sm text-blue-700 space-y-2 list-decimal list-inside">
                  <li>Open Telegram and search for <strong>@SYNCHRO_Bot</strong></li>
                  <li>Send <code className="bg-white/50 px-1 rounded">/start</code></li>
                  <li>Send <code className="bg-white/50 px-1 rounded">/link your-email@example.com</code></li>
                  <li>Bot will confirm linking — you're ready!</li>
                </ol>
              </div>
            )}
          </div>
        )}

        {/* Navigation */}
        <div className="flex justify-between pt-6 border-t border-synchro-border">
          {currentStep > 1 && (
            <button onClick={handleBack} className="synchro-btn-secondary">
              ← Back
            </button>
          )}
          {currentStep < steps.length ? (
            <button onClick={handleNext} className="synchro-btn-primary">
              Next →
            </button>
          ) : (
            <button onClick={handleComplete} className="synchro-btn-gold">
              <Zap className="w-4 h-4 mr-2" /> Launch SYNCHRO
            </button>
          )}
        </div>
      </div>
    </div>
  );
}