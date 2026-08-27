import { cn } from '../utils/cn';
import { 
  FileBarChart, 
  Download, 
  Calendar, 
  TrendingUp, 
  Award,
  Mail,
  CheckCircle2,
  Loader2
} from 'lucide-react';
import { useState } from 'react';

const reportTypes = [
  { 
    id: 'weekly', 
    label: 'Weekly Performance', 
    desc: 'Equity curve, win rate, P&L breakdown, risk metrics',
    icon: FileBarChart,
    frequency: 'Every Monday 00:00 UTC',
  },
  { 
    id: 'monthly', 
    label: 'Monthly Deep Dive', 
    desc: 'Symbol analysis, regime performance, evolution log',
    icon: Award,
    frequency: '1st of month 00:00 UTC',
  },
  { 
    id: 'quarterly', 
    label: 'Quarterly Review', 
    desc: 'Strategy assessment, parameter optimization, risk audit',
    icon: TrendingUp,
    frequency: 'Quarterly 00:00 UTC',
  },
];

const mockReports = [
  { id: 'rpt-1', type: 'weekly', title: 'Week 3 • Jan 15-21', date: '2024-01-22', status: 'ready', size: '2.4 MB' },
  { id: 'rpt-2', type: 'weekly', title: 'Week 2 • Jan 8-14', date: '2024-01-15', status: 'ready', size: '2.1 MB' },
  { id: 'rpt-3', type: 'weekly', title: 'Week 1 • Jan 1-7', date: '2024-01-08', status: 'ready', size: '1.9 MB' },
  { id: 'rpt-4', type: 'monthly', title: 'December 2023', date: '2024-01-01', status: 'ready', size: '8.7 MB' },
  { id: 'rpt-5', type: 'monthly', title: 'November 2023', date: '2023-12-01', status: 'ready', size: '7.3 MB' },
  { id: 'rpt-6', type: 'quarterly', title: 'Q4 2023', date: '2024-01-01', status: 'ready', size: '15.2 MB' },
];

export function Reports() {
  const [generating, setGenerating] = useState<string | null>(null);

  const generateReport = async (typeId: string) => {
    setGenerating(typeId);
    await new Promise(r => setTimeout(r, 2000));
    setGenerating(null);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-synchro-text-primary">Reports</h1>
          <p className="text-synchro-text-secondary">Auto-generated performance reports — PDF & CSV exports</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="synchro-btn-secondary px-4 py-2">
            <Mail className="w-4 h-4 mr-2" /> Email Settings
          </button>
        </div>
      </div>

      {/* Report Types */}
      <section>
        <h2 className="text-lg font-semibold text-synchro-text-primary mb-4">Report Templates</h2>
        <div className="grid md:grid-cols-3 gap-4">
          {reportTypes.map(report => (
            <ReportTemplateCard key={report.id} report={report} onGenerate={generateReport} generating={generating === report.id} />
          ))}
        </div>
      </section>

      {/* Generated Reports */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-synchro-text-primary">Generated Reports</h2>
          <select className="synchro-input w-auto">
            <option value="all">All Reports</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
            <option value="quarterly">Quarterly</option>
          </select>
        </div>

        <div className="synchro-card overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-synchro-border bg-synchro-border/50">
                <th className="text-left p-4 text-xs font-medium text-synchro-text-secondary uppercase tracking-wider">Report</th>
                <th className="text-left p-4 text-xs font-medium text-synchro-text-secondary uppercase tracking-wider">Period</th>
                <th className="text-center p-4 text-xs font-medium text-synchro-text-secondary uppercase tracking-wider">Type</th>
                <th className="text-center p-4 text-xs font-medium text-synchro-text-secondary uppercase tracking-wider">Date</th>
                <th className="text-center p-4 text-xs font-medium text-synchro-text-secondary uppercase tracking-wider">Size</th>
                <th className="text-center p-4 text-xs font-medium text-synchro-text-secondary uppercase tracking-wider">Status</th>
                <th className="text-right p-4 text-xs font-medium text-synchro-text-secondary uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody>
              {mockReports.map(report => (
                <tr key={report.id} className="border-b border-synchro-border/50 hover:bg-synchro-border/50">
                  <td className="p-4">
                    <div className="font-medium text-synchro-text-primary">{report.title}</div>
                  </td>
                  <td className="p-4 text-synchro-text-secondary">{report.type.charAt(0).toUpperCase() + report.type.slice(1)}</td>
                  <td className="p-4 text-center">
                    <span className={cn(
                      'inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium',
                      report.type === 'weekly' ? 'bg-blue-100 text-blue-800' :
                      report.type === 'monthly' ? 'bg-purple-100 text-purple-800' :
                      'bg-amber-100 text-amber-800'
                    )}>
                      {report.type}
                    </span>
                  </td>
                  <td className="p-4 text-center text-synchro-text-secondary">{report.date}</td>
                  <td className="p-4 text-center text-synchro-text-secondary">{report.size}</td>
                  <td className="p-4 text-center">
                    <span className={cn(
                      'inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium',
                      report.status === 'ready' ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'
                    )}>
                      <CheckCircle2 className="w-3 h-3" /> {report.status}
                    </span>
                  </td>
                  <td className="p-4 text-right">
                    <button className="synchro-btn-secondary px-3 py-1.5 text-sm">
                      <Download className="w-4 h-4 mr-1" /> PDF
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Auto-Email Settings */}
      <section className="synchro-card p-6">
        <h3 className="text-lg font-semibold text-synchro-text-primary mb-4 flex items-center gap-2">
          <Mail className="w-5 h-5" /> Auto-Email Settings
        </h3>
        <p className="text-sm text-synchro-text-secondary mb-6">Configure automatic report delivery to your email</p>
        
        <div className="grid md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <h4 className="font-medium text-synchro-text-primary">Weekly Report</h4>
            <EmailSetting 
              label="Send Weekly Report" 
              checked={true} 
              desc="Every Monday 06:00 UTC" 
            />
            <EmailSetting 
              label="Include CSV Export" 
              checked={false} 
              desc="Attach raw trade data CSV" 
            />
          </div>
          <div className="space-y-4">
            <h4 className="font-medium text-synchro-text-primary">Monthly Report</h4>
            <EmailSetting 
              label="Send Monthly Report" 
              checked={true} 
              desc="1st of month 06:00 UTC" 
            />
            <EmailSetting 
              label="Include Evolution Log" 
              checked={true} 
              desc="Attach parameter change history" 
            />
          </div>
        </div>
      </section>
    </div>
  );
}

function ReportTemplateCard({ report, onGenerate, generating }: { report: typeof reportTypes[0]; onGenerate: (id: string) => void; generating: boolean }) {
  return (
    <div className="synchro-card p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-4">
        <div className={cn('w-12 h-12 rounded-xl flex items-center justify-center', `${report.id === 'weekly' ? 'bg-blue-100 text-blue-600' : report.id === 'monthly' ? 'bg-purple-100 text-purple-600' : 'bg-amber-100 text-amber-600'}`)}>
          <report.icon className="w-6 h-6" />
        </div>
      </div>
      <h3 className="text-lg font-semibold text-synchro-text-primary mb-1">{report.label}</h3>
      <p className="text-sm text-synchro-text-secondary mb-3">{report.desc}</p>
      <div className="flex items-center gap-2 text-xs text-synchro-text-secondary mb-4">
        <Calendar className="w-3 h-3" />
        <span>{report.frequency}</span>
      </div>
      <button
        onClick={() => onGenerate(report.id)}
        disabled={generating}
        className="w-full synchro-btn-primary"
      >
        {generating ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin mr-2" />
            Generating...
          </>
        ) : (
          'Generate Now'
        )}
      </button>
    </div>
  );
}

function EmailSetting({ label, checked, desc }: { label: string; checked: boolean; desc: string }) {
  return (
    <label className="flex items-center justify-between cursor-pointer">
      <div>
        <p className="font-medium text-synchro-text-primary">{label}</p>
        <p className="text-xs text-synchro-text-secondary">{desc}</p>
      </div>
      <input
        type="checkbox"
        checked={checked}
        className="w-5 h-5 rounded border-synchro-border text-synchro-navy focus:ring-synchro-navy"
      />
    </label>
  );
}