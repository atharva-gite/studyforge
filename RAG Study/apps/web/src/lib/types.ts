export type User = {
  id: string;
  email: string;
  name: string;
};

export type Course = {
  id: string;
  name: string;
  code: string | null;
  description: string | null;
  role: "OWNER" | "MEMBER";
  document_count: number;
  created_at: string;
  updated_at: string;
};

export type DocumentRecord = {
  id: string;
  course_id: string;
  title: string;
  document_type: string;
  status: string;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  version_number: number;
  version_id: string;
  error: string | null;
  created_at: string;
  duplicate: boolean;
};

export const DOCUMENT_TYPES = [
  ["SYLLABUS", "Syllabus"],
  ["LECTURE", "Lecture"],
  ["TEXTBOOK", "Textbook"],
  ["ASSIGNMENT", "Assignment"],
  ["PAST_PAPER", "Past paper"],
  ["ANNOUNCEMENT", "Announcement"],
  ["OTHER", "Other"],
] as const;

export function documentTypeLabel(value: string): string {
  return DOCUMENT_TYPES.find(([key]) => key === value)?.[1] ?? value;
}

export function statusLabel(status: string): string {
  switch (status) {
    case "UPLOADED":
      return "Uploaded";
    case "PROCESSING":
      return "Processing";
    case "EXTRACTING":
      return "Extracting text";
    case "CHUNKING":
      return "Chunking";
    case "EMBEDDING":
      return "Embedding";
    case "INDEXING":
      return "Indexing";
    case "READY":
      return "Ready";
    case "FAILED":
      return "Failed";
    default:
      return status;
  }
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
