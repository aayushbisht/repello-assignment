export interface SearchResultItem {
  title: string;
  url: string;
  content?: string;
}

// Response from /api/fetch-links
export interface FetchedLinksResponse { 
  query: string;
  results: SearchResultItem[];
  total_results?: number;
}

export interface AnalysisItem {
  question: string;
  analysis_content: string;
}

export interface AiResponse {
  sub_questions: string[];
  analysis: AnalysisItem[];
  synthesis: string[];
  final_answer: string[];
  sources: string[];
}

export type DisplayStage =
  | "idle"
  | "fetchingLinks"
  | "gatheringLinks"
  | "fetchingAiAnalysis"
  | "subquestions"
  | "analysis"
  | "synthesis"
  | "final"
  | "error";

// For storing chat history
export interface ChatMessage {
  id?: string; // DB id
  session_id?: string; // DB session_id
  user_id?: string; // DB user_id
  query: string;
  response?: AiResponse | null;      // Present if the AI processing completed successfully, allow null
  fetchedLinks?: FetchedLinksResponse | null; // Intermediate fetched links, allow null
  error?: string | null;             // Present if an error occurred at any stage for this query, allow null
  stage: DisplayStage | 'final'; // Reflects the stage when this item was last updated or completed
  created_at?: string; // Timestamp
}

export interface ChatSession {
  id: string; // DB id
  user_id: string; // DB user_id
  created_at: string; // Timestamp
  session_name?: string | null; // Optional name for the session
  // Could also include last_message_preview or similar here
}