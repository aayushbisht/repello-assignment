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