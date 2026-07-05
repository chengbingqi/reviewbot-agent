import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { MultiFileReviewPanel } from './MultiFileReviewPanel';

vi.mock('../api/reviewbotClient', () => ({
  streamReview: vi.fn()
}));

describe('MultiFileReviewPanel', () => {
  it('shows selected Python files with preview and remove controls', async () => {
    const user = userEvent.setup();
    const { container } = render(<MultiFileReviewPanel />);
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['def hello():\n    print("hello")\n'], 'main.py', {
      type: 'text/x-python'
    });

    await user.upload(input, file);

    expect(await screen.findByText('main.py')).toBeInTheDocument();
    expect(screen.getByText(/3 lines/)).toBeInTheDocument();
    expect(screen.getByText('waiting')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Preview' }));
    expect(screen.getByText(/def hello/)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Remove' }));
    await waitFor(() => expect(screen.queryByText('main.py')).not.toBeInTheDocument());
  });

  it('can clear all selected files', async () => {
    const user = userEvent.setup();
    const { container } = render(<MultiFileReviewPanel />);
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    const files = [
      new File(['print("a")'], 'a.py', { type: 'text/x-python' }),
      new File(['print("b")'], 'b.py', { type: 'text/x-python' })
    ];

    await user.upload(input, files);
    expect(await screen.findByText('a.py')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Clear Files' }));
    expect(screen.queryByText('a.py')).not.toBeInTheDocument();
    expect(screen.queryByText('b.py')).not.toBeInTheDocument();
  });
});
