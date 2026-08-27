import { cn } from '../utils/cn';

const phases = [
  { id: 0, label: 'Foundations', desc: 'Setup & Auth' },
  { id: 1, label: 'Data & Exec', desc: 'Deriv + EA' },
  { id: 2, label: 'Intelligence', desc: 'HMM + APEX' },
  { id: 3, label: 'Learning', desc: 'Patterns + Evolution' },
  { id: 4, label: 'Product', desc: 'Dashboard + App' },
  { id: 5, label: 'Integration', desc: 'Beta + Launch' },
];

interface PhaseJourneyProps {
  currentPhase: number;
}

export function PhaseJourney({ currentPhase }: PhaseJourneyProps) {
  return (
    <div className="synchro-card p-4">
      <h3 className="text-lg font-semibold text-synchro-text-primary mb-4">Phase Journey</h3>
      <div className="relative">
        {/* Progress line */}
        <div className="absolute left-0 right-0 top-20 h-1 bg-synchro-border -translate-y-1/2" />
        <div className="absolute left-0 top-20 h-1 bg-synchro-navy -translate-y-1/2 transition-all duration-500" 
          style={{ width: `${((currentPhase) / (phases.length - 1)) * 100}%` }} 
        />
        
        <div className="flex items-center justify-between relative z-10">
          {phases.map((phase, index) => {
            const isCompleted = index < currentPhase;
            const isCurrent = index === currentPhase;
            
            return (
              <div key={phase.id} className="flex flex-col items-center">
                <div className={cn(
                  'w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold transition-all duration-300 relative z-10',
                  isCompleted 
                    ? 'bg-synchro-navy text-white' 
                    : isCurrent 
                      ? 'bg-synchro-gold text-white shadow-lg shadow-amber-300/50 ring-4 ring-amber-100' 
                      : 'bg-synchro-border text-synchro-text-secondary'
                )}>
                  {isCompleted ? '✓' : index + 1}
                </div>
                <div className="mt-2 text-center w-24">
                  <p className={cn(
                    'text-xs font-medium truncate',
                    isCompleted || isCurrent ? 'text-synchro-text-primary' : 'text-synchro-text-secondary'
                  )}>
                    {phase.label}
                  </p>
                  <p className="text-[10px] text-synchro-text-secondary mt-0.5">
                    {phase.desc}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
      
      <div className="mt-6 p-3 bg-synchro-border/50 rounded-xl">
        <p className="text-sm text-synchro-text-secondary text-center">
          Currently in <strong className="text-synchro-text-primary">Phase {currentPhase}</strong> —{" "}
          {phases[currentPhase]?.label || 'Building'}
        </p>
      </div>
    </div>
  );
}