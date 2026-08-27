import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Onboarding } from './pages/Onboarding';
import { CommandDashboard } from './pages/CommandDashboard';
import { LiveCharts } from './pages/LiveCharts';
import { TradeCards } from './pages/TradeCards';
import { HistoryInsights } from './pages/HistoryInsights';
import { ApprovalCenter } from './pages/ApprovalCenter';
import { Settings } from './pages/Settings';
import { Reports } from './pages/Reports';
import { DemoReplay } from './pages/DemoReplay';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="onboarding" element={<Onboarding />} />
          <Route path="dashboard" element={<CommandDashboard />} />
          <Route path="charts" element={<LiveCharts />} />
          <Route path="trades" element={<TradeCards />} />
          <Route path="history" element={<HistoryInsights />} />
          <Route path="approvals" element={<ApprovalCenter />} />
          <Route path="settings" element={<Settings />} />
          <Route path="reports" element={<Reports />} />
          <Route path="demo" element={<DemoReplay />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;