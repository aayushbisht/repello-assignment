"use client";

import React from 'react';
import { AiResponse, DisplayStage, AnalysisItem, FetchedLinksResponse } from '../types';

interface ThinkingProcessDisplayProps {
  fetchedLinksData: FetchedLinksResponse | null;
  aiAnalysisData: AiResponse | null;
  displayStage: DisplayStage;
  currentLinkIndex?: number;
  loadingMessage?: string;
}

const ThinkingProcessDisplay: React.FC<ThinkingProcessDisplayProps> = ({ 
  fetchedLinksData,
  aiAnalysisData, 
  displayStage, 
  currentLinkIndex,
  loadingMessage
}) => {

  const renderContent = () => {
    switch (displayStage) {
      case 'fetchingLinks':
      case 'fetchingAiAnalysis':
        return (
          <div className="thinking-bubble">
            <h2>{loadingMessage || "Processing..."}</h2>
          </div>
        );
      case 'gatheringLinks':
        if (!fetchedLinksData || fetchedLinksData.results.length === 0 || typeof currentLinkIndex === 'undefined') return null;
        const linkToShow = fetchedLinksData.results[currentLinkIndex];
        return (
          <div className="thinking-bubble">
            <h2>Gathering data...</h2>
            {linkToShow && (
              <p>From: <a href={linkToShow.url} target="_blank" rel="noopener noreferrer">{linkToShow.title || linkToShow.url}</a></p>
            )}
            <p>({currentLinkIndex + 1} of {fetchedLinksData.results.length})</p>
          </div>
        );
      case 'subquestions':
        if (!aiAnalysisData) return null;
        return (
          <div className="thinking-bubble">
            <h2>Thinking: Sub-questions...</h2>
            <ul>
              {aiAnalysisData.sub_questions.map((sq, index) => (
                <li key={`sq-${index}`}>{sq}</li>
              ))}
            </ul>
          </div>
        );
      case 'analysis':
        if (!aiAnalysisData) return null;
        return (
          <div className="thinking-bubble card">
            <h2 className="thinking-subtitle">Analyzing Information</h2>
            <ul className="analysis-list">
              {aiAnalysisData.analysis.map((item: AnalysisItem, index) => (
                <li key={`analysis-${index}`} className="analysis-item">
                  <p className="analysis-question"><strong>Question:</strong> {item.question}</p>
                  {item.analysis_content && item.analysis_content.trim() !== '' && (
                     <p className="analysis-answer">{item.analysis_content}</p>
                  )}
                </li>
              ))}
            </ul>
          </div>
        );
      case 'synthesis':
        if (!aiAnalysisData) return null;
        return (
          <div className="thinking-bubble card">
            <h2 className="thinking-subtitle">Synthesizing Insights</h2>
            <ul className="synthesis-list">
              {aiAnalysisData.synthesis.map((point, index) => (
                <li key={`synthesis-${index}`} className="synthesis-point">{point}</li>
              ))}
            </ul>
          </div>
        );
      default:
        return null;
    }
  };

  return <>{renderContent()}</>;
};

export default ThinkingProcessDisplay; 