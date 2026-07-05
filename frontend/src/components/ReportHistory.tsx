import { useEffect, useState } from 'react';
import { getReport, listReports } from '../api/reviewbotClient';
import type { ReportDetail, ReportIndexItem } from '../types';
import { ReportDetail as ReportDetailView } from './ReportDetail';

export function ReportHistory() {
  const [reports, setReports] = useState<ReportIndexItem[]>([]);
  const [detail, setDetail] = useState<ReportDetail | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function refresh() {
    setLoading(true);
    setError('');
    try {
      setReports(await listReports());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function openReport(reviewId: string) {
    setError('');
    try {
      setDetail(await getReport(reviewId));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return (
    <div className="history-grid">
      <section className="panel">
        <div className="panel-heading">
          <h2>Report History</h2>
          <button type="button" onClick={refresh} disabled={loading}>
            Refresh
          </button>
        </div>
        {error && <div className="alert">{error}</div>}
        <div className="history-list">
          {reports.length === 0 ? (
            <p className="muted">No saved reports yet.</p>
          ) : (
            reports.map((report) => (
              <button
                type="button"
                className="history-item"
                key={report.review_id}
                onClick={() => void openReport(report.review_id)}
              >
                <strong>{report.review_id}</strong>
                <span>{report.created_at}</span>
                <span>
                  {report.mode} · {report.file_count} files
                </span>
                <span className="muted">{report.summary}</span>
              </button>
            ))
          )}
        </div>
      </section>
      <ReportDetailView detail={detail} onBack={() => setDetail(null)} />
    </div>
  );
}
