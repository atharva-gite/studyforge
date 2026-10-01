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

export type Citation = {
  chunk_id: string;
  document_id: string;
  document_title: string;
  page_start: number | null;
  page_end: number | null;
  section: string | null;
};

export type QuestionResult = {
  status: "answered" | "insufficient_evidence";
  answer: string | null;
  citations: Citation[];
};

export type StudyCard = {
  id: string;
  position: number;
  front: string;
  back: string;
  latest_rating: "AGAIN" | "KNOWN" | null;
  chunk_id: string | null;
  document_id: string | null;
  document_title: string | null;
  page_start: number | null;
};

export type Deck = {
  id: string;
  title: string;
  next_card_id: string | null;
  cards: StudyCard[];
};

export type DeckResult = {
  status: "created" | "insufficient_evidence";
  deck: Deck | null;
};

export type QuizQuestion = {
  id: string;
  position: number;
  prompt: string;
  options: string[];
};

export type Quiz = {
  id: string;
  title: string;
  questions: QuizQuestion[];
};

export type QuizResult = {
  status: "created" | "insufficient_evidence";
  quiz: Quiz | null;
};

export type AttemptResult = {
  question_id: string;
  prompt: string;
  selected_option_index: number | null;
  correct_option_index: number;
  correct: boolean;
  explanation: string | null;
  citation: Citation | null;
};

export type Attempt = {
  score: number;
  results: AttemptResult[];
};

export type StudySessionItem = {
  id: string;
  scheduled_on: string;
  duration_minutes: number;
  activity: string;
  focus: string | null;
  status: string;
};

export type StudyPlan = {
  id: string;
  exam_title: string;
  exam_date: string;
  hours_per_day: number;
  sessions: StudySessionItem[];
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
