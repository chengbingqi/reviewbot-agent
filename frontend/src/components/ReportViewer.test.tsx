import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ReportViewer } from './ReportViewer';

describe('ReportViewer', () => {
  it('renders markdown headings, tables, lists, and code blocks', () => {
    render(
      <ReportViewer
        report={`# Review\n\n- item\n\n| Tool | Status |\n| --- | --- |\n| Ruff | pass |\n\n\`\`\`python\nprint("ok")\n\`\`\``}
      />
    );

    expect(screen.getByRole('heading', { name: 'Review' })).toBeInTheDocument();
    expect(screen.getByText('item')).toBeInTheDocument();
    expect(screen.getByRole('table')).toBeInTheDocument();
    expect(screen.getByText('print("ok")')).toBeInTheDocument();
  });

  it('keeps copy and download actions available', () => {
    render(<ReportViewer report="# Ready" />);

    expect(screen.getByRole('button', { name: 'Copy Report' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Download Markdown' })).toBeEnabled();
  });
});
