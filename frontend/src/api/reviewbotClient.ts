import type { ReportDetail, ReportIndexItem, ReviewEvent } from '../types';

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
export const API_AUTH_TOKEN = import.meta.env.VITE_AUTH_TOKEN || '';
export const AUTH_STATUS = API_AUTH_TOKEN ? 'Token configured' : 'Disabled';

function buildUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

export function getAuthHeaders(): Record<string, string> {
  return API_AUTH_TOKEN ? { Authorization: `Bearer ${API_AUTH_TOKEN}` } : {};
}

export function buildReportHtmlUrl(reviewId: string): string {
  return buildUrl(`/reports/${encodeURIComponent(reviewId)}/html`);
}

export async function getHealth(): Promise<{ status: string }> {
  const response = await fetch(buildUrl('/health'));
  if (!response.ok) {
    throw new Error(`Health check failed: HTTP ${response.status}`);
  }
  return response.json();
}

export async function listReports(): Promise<ReportIndexItem[]> {
  const response = await fetch(buildUrl('/reports'), {
    headers: getAuthHeaders()
  });
  if (!response.ok) {
    throw new Error(`Report history failed: HTTP ${response.status}`);
  }
  return response.json();
}

export async function getReport(reviewId: string): Promise<ReportDetail> {
  const response = await fetch(buildUrl(`/reports/${encodeURIComponent(reviewId)}`), {
    headers: getAuthHeaders()
  });
  if (!response.ok) {
    throw new Error(`Report detail failed: HTTP ${response.status}`);
  }
  return response.json();
}

export async function getReportHtmlBlobUrl(reviewId: string): Promise<string> {
  const response = await fetch(buildReportHtmlUrl(reviewId), {
    headers: getAuthHeaders()
  });
  if (!response.ok) {
    throw new Error(`HTML preview failed: HTTP ${response.status}`);
  }
  const blob = await response.blob();
  return URL.createObjectURL(blob);
}

export function parseSseBlock(block: string): ReviewEvent | null {
  const dataLines = block
    .split('\n')
    .map((line) => line.trimEnd())
    .filter((line) => line.startsWith('data: '))
    .map((line) => line.slice(6));

  if (dataLines.length === 0) {
    return null;
  }

  const raw = dataLines.join('\n');
  try {
    const parsed = JSON.parse(raw) as ReviewEvent;
    return {
      ...parsed,
      receivedAt: new Date().toLocaleTimeString()
    };
  } catch (error) {
    throw new Error(`Failed to parse SSE JSON: ${raw.slice(0, 160)}`);
  }
}

export async function streamReview(
  endpoint: string,
  payload: unknown,
  onEvent: (event: ReviewEvent) => void,
  onError: (error: Error) => void
): Promise<void> {
  try {
    const response = await fetch(buildUrl(endpoint), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(`Review request failed: HTTP ${response.status}`);
    }

    if (!response.body) {
      throw new Error('Response stream is unavailable.');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split(/\r?\n\r?\n/);
      buffer = blocks.pop() ?? '';

      for (const block of blocks) {
        if (!block.trim()) continue;
        const event = parseSseBlock(block);
        if (event) onEvent(event);
      }
    }

    if (buffer.trim()) {
      const event = parseSseBlock(buffer);
      if (event) onEvent(event);
    }
  } catch (error) {
    onError(error instanceof Error ? error : new Error(String(error)));
  }
}
