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

// This is the structure of the AI analysis part, matches what /api/fetch-ai-analysis returns
// and is used in the main page state as aiAnalysisData
export interface AiResponse {
  sub_questions: string[];
  analysis: AnalysisItem[];
  synthesis: string[];
  final_answer: string[];
  sources: string[];
}

// For display stages - gatheringLinks will now use FetchedLinksResponse
// subquestions, analysis, synthesis, final will use AiResponse
export type DisplayStage =
  | "idle"
  | "fetchingLinks" // Renamed for clarity that it's an active fetch
  | "gatheringLinks" // Displaying fetched links one by one
  | "fetchingAiAnalysis" // Active fetch for AI part
  | "subquestions"
  | "analysis"
  | "synthesis"
  | "final"
  | "error"; // Added an explicit error stage 