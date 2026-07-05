import { useState } from 'react';
import { HealthStatus } from './components/HealthStatus';
import { CodeReviewPanel } from './components/CodeReviewPanel';
import { MultiFileReviewPanel } from './components/MultiFileReviewPanel';
import { ReportHistory } from './components/ReportHistory';

type Tab = 'single' | 'files' | 'reports';

export default function App() {
  const [tab, setTab] = useState<Tab>('single');

  return (
    <main>
      <header className="app-header">
        <div>
          <h1>ReviewBot Web UI</h1>
          <p>Code review workflow with SSE progress and report history.</p>
        </div>
        <HealthStatus />
      </header>

      <nav className="tabs">
        <button className={tab === 'single' ? 'active' : ''} onClick={() => setTab('single')}>
          Single Code Review
        </button>
        <button className={tab === 'files' ? 'active' : ''} onClick={() => setTab('files')}>
          Multi-file Review
        </button>
        <button className={tab === 'reports' ? 'active' : ''} onClick={() => setTab('reports')}>
          Reports
        </button>
      </nav>

      {tab === 'single' && <CodeReviewPanel />}
      {tab === 'files' && <MultiFileReviewPanel />}
      {tab === 'reports' && <ReportHistory />}
    </main>
  );
}
