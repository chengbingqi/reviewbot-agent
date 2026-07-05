import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { HealthStatus } from './HealthStatus';

const getHealthMock = vi.fn();

vi.mock('../api/reviewbotClient', () => ({
  API_BASE_URL: 'http://127.0.0.1:8000',
  AUTH_STATUS: 'Disabled',
  getHealth: () => getHealthMock()
}));

describe('HealthStatus', () => {
  beforeEach(() => {
    getHealthMock.mockReset();
  });

  it('shows a clear hint when the backend is offline', async () => {
    getHealthMock.mockRejectedValue(new Error('network down'));
    render(<HealthStatus />);

    await waitFor(() => {
    expect(screen.getByText(/Backend Offline/)).toBeInTheDocument();
    });
    expect(screen.getByText(/uvicorn api_server:app/)).toBeInTheDocument();
    expect(screen.getByText('Auth: Disabled')).toBeInTheDocument();
  });
});
