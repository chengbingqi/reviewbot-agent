export type ReviewEvent = {
  event: string;
  node: string | null;
  message: string;
  data: Record<string, unknown> | null;
  error: string | null;
  receivedAt?: string;
};

export type ReviewFile = {
  path: string;
  content: string;
  size?: number;
  lineCount?: number;
};

export type FileProgress = {
  filePath: string;
  fileIndex?: number;
  totalFiles?: number;
  stage: string;
  status: string;
};

export type ReportIndexItem = {
  review_id: string;
  created_at: string;
  mode: string;
  target: string;
  file_count: number;
  duration_ms?: number | null;
  model_name?: string | null;
  markdown_path: string;
  html_path: string;
  summary: string;
};

export type ReportDetail = {
  metadata: ReportIndexItem;
  markdown: string;
  markdown_path: string;
  html_path: string | null;
};
