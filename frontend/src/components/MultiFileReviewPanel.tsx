import { useMemo, useState } from 'react';
import { streamReview } from '../api/reviewbotClient';
import type { FileProgress, ReviewEvent, ReviewFile } from '../types';
import { EventTimeline } from './EventTimeline';
import { FileProgressList } from './FileProgressList';
import { ReportViewer } from './ReportViewer';

const MAX_SELECTED_FILES = 20;
const PREVIEW_LINE_LIMIT = 160;

function updateFileProgress(current: FileProgress[], event: ReviewEvent): FileProgress[] {
  const data = event.data ?? {};
  const filePath = data.file_path;
  if (typeof filePath !== 'string') return current;

  const next: FileProgress = {
    filePath,
    fileIndex: typeof data.file_index === 'number' ? data.file_index : undefined,
    totalFiles: typeof data.total_files === 'number' ? data.total_files : undefined,
    stage: typeof data.stage === 'string' ? data.stage : event.event,
    status: typeof data.status === 'string' ? data.status : event.event
  };

  const without = current.filter((item) => item.filePath !== filePath);
  return [...without, next].sort((a, b) => (a.fileIndex ?? 0) - (b.fileIndex ?? 0));
}

function lineCount(content: string): number {
  if (!content) return 0;
  return content.split(/\r?\n/).length;
}

function formatBytes(size = 0): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function previewContent(content: string): { text: string; truncated: boolean } {
  const lines = content.split(/\r?\n/);
  if (lines.length <= PREVIEW_LINE_LIMIT) {
    return { text: content, truncated: false };
  }
  return {
    text: lines.slice(0, PREVIEW_LINE_LIMIT).join('\n'),
    truncated: true
  };
}

export function MultiFileReviewPanel() {
  const [files, setFiles] = useState<ReviewFile[]>([]);
  const [events, setEvents] = useState<ReviewEvent[]>([]);
  const [progress, setProgress] = useState<FileProgress[]>([]);
  const [report, setReport] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [previewPath, setPreviewPath] = useState('');

  const totalChars = useMemo(
    () => files.reduce((total, file) => total + file.content.length, 0),
    [files]
  );

  const previewFile = useMemo(
    () => files.find((file) => file.path === previewPath) ?? null,
    [files, previewPath]
  );

  const preview = previewFile ? previewContent(previewFile.content) : null;

  function statusForFile(path: string): string {
    return progress.find((item) => item.filePath === path)?.status ?? 'waiting';
  }

  async function onFilesSelected(fileList: FileList | null) {
    if (!fileList) return;

    const selectedFiles = Array.from(fileList);
    const unsupported = selectedFiles.filter((file) => !file.name.endsWith('.py'));
    let selected = selectedFiles.filter((file) => file.name.endsWith('.py'));
    const messages: string[] = [];

    if (unsupported.length > 0) {
      messages.push(`Unsupported files ignored: ${unsupported.map((file) => file.name).join(', ')}`);
    }
    if (selected.length > MAX_SELECTED_FILES) {
      messages.push(`Only the first ${MAX_SELECTED_FILES} Python files were added.`);
      selected = selected.slice(0, MAX_SELECTED_FILES);
    }

    const readFiles = await Promise.all(
      selected.map(async (file) => {
        const content = await file.text();
        return {
          path: file.webkitRelativePath || file.name,
          content,
          size: file.size,
          lineCount: lineCount(content)
        };
      })
    );

    const emptyFiles = readFiles.filter((file) => file.content.trim().length === 0);
    if (emptyFiles.length > 0) {
      messages.push(`Empty files need content before review: ${emptyFiles.map((file) => file.path).join(', ')}`);
    }

    setFiles(readFiles);
    setProgress([]);
    setPreviewPath(readFiles[0]?.path ?? '');
    setError(readFiles.length === 0 ? 'Please choose at least one .py file.' : messages.join(' '));
  }

  function removeFile(path: string) {
    setFiles((items) => {
      const next = items.filter((item) => item.path !== path);
      if (previewPath === path) {
        setPreviewPath(next[0]?.path ?? '');
      }
      return next;
    });
    setProgress((items) => items.filter((item) => item.filePath !== path));
  }

  function clearFiles() {
    setFiles([]);
    setProgress([]);
    setPreviewPath('');
    setError('');
  }

  async function startReview() {
    if (files.length === 0) {
      setError('Please choose at least one .py file.');
      return;
    }

    const emptyFiles = files.filter((file) => file.content.trim().length === 0);
    if (emptyFiles.length > 0) {
      setError(`Empty files need content before review: ${emptyFiles.map((file) => file.path).join(', ')}`);
      return;
    }

    setEvents([]);
    setProgress([]);
    setReport('');
    setError('');
    setLoading(true);
    await streamReview(
      '/review-files',
      { files: files.map((file) => ({ path: file.path, content: file.content })) },
      (event) => {
        setEvents((items) => [...items, event]);
        if (['file_start', 'file_progress', 'file_end'].includes(event.event)) {
          setProgress((items) => updateFileProgress(items, event));
        }
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
          <h2>Multi-file Review</h2>
          <button type="button" onClick={startReview} disabled={loading || files.length === 0}>
            {loading ? 'Reviewing...' : 'Start Review'}
          </button>
        </div>
        {error && <div className="alert">{error}</div>}
        <input type="file" multiple accept=".py" onChange={(event) => void onFilesSelected(event.target.files)} />
        <div className="muted">
          {files.length} files selected | {totalChars.toLocaleString()} characters
        </div>
        {files.length > 0 && (
          <div className="selected-file-tools">
            <button type="button" onClick={clearFiles} disabled={loading}>
              Clear Files
            </button>
          </div>
        )}
        {files.length > 0 && (
          <div className="selected-file-list">
            {files.map((file) => (
              <div className="selected-file-row" key={file.path}>
                <div className="file-meta">
                  <strong>{file.path}</strong>
                  <span>
                    {formatBytes(file.size)} | {file.lineCount ?? lineCount(file.content)} lines
                  </span>
                </div>
                <span className={`badge ${statusForFile(file.path)}`}>{statusForFile(file.path)}</span>
                <div className="button-row">
                  <button type="button" onClick={() => setPreviewPath(file.path)}>
                    Preview
                  </button>
                  <button type="button" onClick={() => removeFile(file.path)} disabled={loading}>
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        {previewFile && preview && (
          <div className="file-preview-panel">
            <div className="panel-heading">
              <h3>Preview: {previewFile.path}</h3>
              {preview.truncated && <span className="muted">Showing first {PREVIEW_LINE_LIMIT} lines.</span>}
            </div>
            <pre className="file-preview">{preview.text}</pre>
          </div>
        )}
      </section>
      <FileProgressList files={progress} />
      <EventTimeline events={events} />
      <ReportViewer report={report} />
    </div>
  );
}
