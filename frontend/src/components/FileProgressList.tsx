import type { FileProgress } from '../types';

type Props = {
  files: FileProgress[];
};

export function FileProgressList({ files }: Props) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Files</h2>
        <span>{files.length}</span>
      </div>
      <div className="file-list">
        {files.length === 0 ? (
          <p className="muted">No file progress yet.</p>
        ) : (
          files.map((file) => (
            <div className="file-row" key={file.filePath}>
              <div>
                <strong>{file.filePath}</strong>
                <div className="muted">
                  {file.fileIndex && file.totalFiles
                    ? `${file.fileIndex}/${file.totalFiles}`
                    : 'queued'}{' '}
                  · {file.stage}
                </div>
              </div>
              <span className={`badge ${file.status}`}>{file.status}</span>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
