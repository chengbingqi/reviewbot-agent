import { useState } from 'react';
import type { ReportDetail as ReportDetailType } from '../types';
import { getReportHtmlBlobUrl } from '../api/reviewbotClient';
import { ReportViewer } from './ReportViewer';

type Props = {
  detail: ReportDetailType | null;
  onBack?: () => void;
};

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return 'N/A';
  return String(value);
}

function downloadMarkdown(report: string, reviewId: string) {
  const blob = new Blob([report], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `${reviewId || 'reviewbot_report'}.md`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function ReportDetail({ detail, onBack }: Props) {
  const [htmlPreviewError, setHtmlPreviewError] = useState('');

  if (!detail) {
    return (
      <section className="panel report-panel">
        <h2>Report Detail</h2>
        <p className="muted">Select a report from history.</p>
      </section>
    );
  }

  const reportDetail = detail;

  async function copyMarkdown() {
    if (!reportDetail.markdown) return;
    await navigator.clipboard.writeText(reportDetail.markdown);
  }

  async function openHtmlPreview() {
    setHtmlPreviewError('');
    if (!reportDetail.html_path) {
      setHtmlPreviewError('HTML preview is not available for this report.');
      return;
    }
    try {
      const blobUrl = await getReportHtmlBlobUrl(reportDetail.metadata.review_id);
      const popup = window.open(blobUrl, '_blank', 'noopener,noreferrer');
      if (!popup) {
        URL.revokeObjectURL(blobUrl);
        setHtmlPreviewError('HTML preview was blocked by the browser popup settings.');
      }
    } catch (error) {
      setHtmlPreviewError(error instanceof Error ? error.message : String(error));
    }
  }

  const metadata = reportDetail.metadata;
  const metadataRows = [
    ['review_id', metadata.review_id],
    ['created_at', metadata.created_at],
    ['mode', metadata.mode],
    ['target', metadata.target],
    ['file_count', metadata.file_count],
    ['duration_ms', metadata.duration_ms],
    ['model_name', metadata.model_name],
    ['markdown_path', reportDetail.markdown_path || metadata.markdown_path],
    ['html_path', reportDetail.html_path || metadata.html_path]
  ];

  return (
    <div>
      <section className="panel">
        <div className="panel-heading">
          <h2>Report Metadata</h2>
          <div className="button-row detail-actions">
            <button type="button" onClick={onBack}>
              Back to Reports
            </button>
            <button type="button" onClick={copyMarkdown} disabled={!reportDetail.markdown}>
              Copy Markdown
            </button>
            <button
              type="button"
              onClick={() => downloadMarkdown(reportDetail.markdown, metadata.review_id)}
              disabled={!reportDetail.markdown}
            >
              Download Markdown
            </button>
            <button type="button" onClick={() => void openHtmlPreview()} disabled={!reportDetail.html_path}>
              Open HTML Preview
            </button>
          </div>
        </div>
        {htmlPreviewError && <div className="alert">{htmlPreviewError}</div>}
        {!reportDetail.html_path && (
          <p className="muted">HTML preview is unavailable because this report has no HTML path.</p>
        )}
        {!reportDetail.markdown && <div className="alert">Markdown content is empty.</div>}
        <div className="metadata-grid">
          {metadataRows.map(([label, value]) => (
            <div key={label}>
              <strong>{label}</strong>
              <span>{displayValue(value)}</span>
            </div>
          ))}
        </div>
      </section>
      <ReportViewer report={reportDetail.markdown} title="Report Detail" />
    </div>
  );
}
