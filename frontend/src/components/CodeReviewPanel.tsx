import { useState } from 'react';
import { streamReview } from '../api/reviewbotClient';
import type { ReviewEvent } from '../types';
import { EventTimeline } from './EventTimeline';
import { ReportViewer } from './ReportViewer';

const DEMO_CODE = `API_KEY = 'abc123'
print(API_KEY)
`;

export function CodeReviewPanel() {
  const [code, setCode] = useState(DEMO_CODE);
  const [events, setEvents] = useState<ReviewEvent[]>([]);
  const [report, setReport] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function startReview() {
    setEvents([]);
    setReport('');
    setError('');
    setLoading(true);
    await streamReview(
      '/review',
      { code },
      (event) => {
        setEvents((items) => [...items, event]);
        if ((event.event === 'done' || event.event === 'review_complete') && event.data) {
          const maybeReport = event.data.report;
          if (typeof maybeReport === 'string') setReport(maybeReport);
        }
      },
      (err) => setError(err.message)
    );
    setLoading(false);
  }

  return (
    <div className="workspace-grid">
      <section className="panel">
        <div className="panel-heading">
          <h2>Single Code Review</h2>
          <button type="button" onClick={startReview} disabled={loading || !code.trim()}>
            {loading ? 'Reviewing...' : 'Start Review'}
          </button>
        </div>
        {error && <div className="alert">{error}</div>}
        <textarea value={code} onChange={(event) => setCode(event.target.value)} />
      </section>
      <EventTimeline events={events} />
      <ReportViewer report={report} />
    </div>
  );
}
