import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ReportHistory } from './ReportHistory';

const listReportsMock = vi.fn();
const getReportMock = vi.fn();

vi.mock('../api/reviewbotClient', () => ({
  getReportHtmlBlobUrl: (reviewId: string) => Promise.resolve(`blob:${reviewId}`),
  listReports: () => listReportsMock(),
  getReport: (reviewId: string) => getReportMock(reviewId)
}));

describe('ReportHistory', () => {
  beforeEach(() => {
    listReportsMock.mockReset();
    getReportMock.mockReset();
  });

  it('loads history and opens report details', async () => {
    listReportsMock.mockResolvedValue([
      {
        review_id: 'review_1',
        created_at: '2026-07-05T12:00:00',
        mode: 'single',
        target: 'code-snippet',
        file_count: 1,
        markdown_path: 'reports/review_1.md',
        html_path: 'reports/review_1.html',
        summary: 'Found issues'
      }
    ]);
    getReportMock.mockResolvedValue({
      metadata: {
        review_id: 'review_1',
        created_at: '2026-07-05T12:00:00',
        mode: 'single',
        target: 'code-snippet',
        file_count: 1,
        markdown_path: 'reports/review_1.md',
        html_path: 'reports/review_1.html',
        summary: 'Found issues'
      },
      markdown: '# Report Detail',
      markdown_path: 'reports/review_1.md',
      html_path: 'reports/review_1.html'
    });

    const user = userEvent.setup();
    render(<ReportHistory />);

    const reportButton = await screen.findByRole('button', { name: /review_1/ });
    await user.click(reportButton);

    await waitFor(() => {
      expect(getReportMock).toHaveBeenCalledWith('review_1');
    });
    expect(screen.getAllByRole('heading', { name: 'Report Detail' }).length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: 'Open HTML Preview' })).toBeEnabled();
  });
});
