import ReactMarkdown from 'react-markdown';
import rehypeSanitize from 'rehype-sanitize';
import remarkGfm from 'remark-gfm';

type Props = {
  report: string;
  title?: string;
};

function downloadMarkdown(report: string) {
  const blob = new Blob([report], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `reviewbot_report_${new Date().toISOString().replace(/[:.]/g, '-')}.md`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function ReportViewer({ report, title = 'Report' }: Props) {
  async function copyReport() {
    if (!report) return;
    await navigator.clipboard.writeText(report);
  }

  function renderReport() {
    if (!report) {
      return <pre className="report-body">No report generated yet.</pre>;
    }

    try {
      return (
        <div className="markdown-body">
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
            {report}
          </ReactMarkdown>
        </div>
      );
    } catch {
      return <pre className="report-body">{report}</pre>;
    }
  }

  return (
    <section className="panel report-panel">
      <div className="panel-heading">
        <h2>{title}</h2>
        <div className="button-row">
          <button type="button" onClick={copyReport} disabled={!report}>
            Copy Report
          </button>
          <button type="button" onClick={() => downloadMarkdown(report)} disabled={!report}>
            Download Markdown
          </button>
        </div>
      </div>
      {renderReport()}
    </section>
  );
}
