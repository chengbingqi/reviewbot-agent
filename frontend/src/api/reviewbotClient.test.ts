import { describe, expect, it, vi } from 'vitest';
import { getAuthHeaders, parseSseBlock } from './reviewbotClient';

describe('parseSseBlock', () => {
  it('parses data JSON blocks', () => {
    const event = parseSseBlock(
      'data: {"event":"file_progress","node":"review_files","message":"ok","data":{"file_path":"app/main.py"},"error":null}\n\n'
    );

    expect(event).toMatchObject({
      event: 'file_progress',
      node: 'review_files',
      message: 'ok',
      error: null
    });
    expect(event?.data?.file_path).toBe('app/main.py');
    expect(event?.receivedAt).toBeTruthy();
  });

  it('returns null for empty non-data blocks', () => {
    expect(parseSseBlock(': keepalive\n\n')).toBeNull();
  });

  it('throws a readable error for invalid JSON', () => {
    expect(() => parseSseBlock('data: {"event":')).toThrow(/Failed to parse SSE JSON/);
  });

  it('does not add Authorization when token is not configured', () => {
    expect(getAuthHeaders()).toEqual({});
  });

  it('adds Authorization when token is configured', async () => {
    vi.stubEnv('VITE_AUTH_TOKEN', 'test-token');
    vi.resetModules();
    const module = await import('./reviewbotClient');
    expect(module.getAuthHeaders()).toEqual({ Authorization: 'Bearer test-token' });
    vi.unstubAllEnvs();
  });
});
