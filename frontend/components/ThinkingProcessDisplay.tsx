"use client";

import React, { useState, useEffect } from 'react';
import { AiResponse, DisplayStage, AnalysisItem, FetchedLinksResponse } from '../types';

interface ThinkingProcessDisplayProps {
  fetchedLinksData: FetchedLinksResponse | null;
  aiAnalysisData: AiResponse | null;
  displayStage: DisplayStage;
  currentLinkIndex?: number;
  loadingMessage?: string;
}

const ITEM_REVEAL_DELAY = 2000;

const ThinkingProcessDisplay: React.FC<ThinkingProcessDisplayProps> = ({ 
  fetchedLinksData,
  aiAnalysisData, 
  displayStage, 
  currentLinkIndex,
  loadingMessage
}) => {
  const [revealedItemCount, setRevealedItemCount] = useState(0);

  useEffect(() => {
    setRevealedItemCount(0);
    if (!aiAnalysisData) return;

    let timer: NodeJS.Timeout;
    let itemsToReveal = 0;

    if (displayStage === 'subquestions') itemsToReveal = aiAnalysisData.sub_questions.length;
    else if (displayStage === 'analysis') itemsToReveal = aiAnalysisData.analysis.length;
    else if (displayStage === 'synthesis') itemsToReveal = aiAnalysisData.synthesis.length;
    else return;

    if (itemsToReveal > 0) {
      const revealNextItem = (currentIndex: number) => {
        if (currentIndex < itemsToReveal) {
          setRevealedItemCount(currentIndex + 1);
          timer = setTimeout(() => revealNextItem(currentIndex + 1), ITEM_REVEAL_DELAY);
        }
      };
      timer = setTimeout(() => revealNextItem(0), ITEM_REVEAL_DELAY / 2);
    }

    return () => clearTimeout(timer);
  }, [displayStage, aiAnalysisData]);

  const commonTextStyle = {
    wordWrap: 'break-word' as 'break-word',
    whiteSpace: 'pre-wrap' as 'pre-wrap',
    maxWidth: '100%',
  };

  const thinkingBubbleStyle = {
    width: '100%',
    boxSizing: 'border-box' as 'border-box',
    overflow: 'hidden',
  };

  const renderContent = () => {
    switch (displayStage) {
      case 'fetchingLinks':
      case 'fetchingAiAnalysis':
        return (
          <div className="thinking-bubble" style={thinkingBubbleStyle}>
            <h2>{loadingMessage || "Processing..."}</h2>
          </div>
        );
      case 'gatheringLinks':
        if (!fetchedLinksData || fetchedLinksData.results.length === 0 || typeof currentLinkIndex === 'undefined') return null;
        const linkToShow = fetchedLinksData.results[currentLinkIndex];
        return (
          <div className="thinking-bubble" style={thinkingBubbleStyle}>
            <h2>Gathering data...</h2>
            {linkToShow && (
              <p style={commonTextStyle}>From: <a href={linkToShow.url} target="_blank" rel="noopener noreferrer">{linkToShow.title || linkToShow.url}</a></p>
            )}
            <p>({currentLinkIndex + 1} of {fetchedLinksData.results.length})</p>
          </div>
        );
      case 'subquestions':
        if (!aiAnalysisData) return null;
        return (
          <div className="thinking-bubble card" style={thinkingBubbleStyle}>
            <h2 className="thinking-subtitle">Thinking ...</h2>
            <ul>
              {aiAnalysisData.sub_questions.slice(0, revealedItemCount).map((sq, index) => (
                <li key={`sq-${index}`} style={commonTextStyle}>{sq}</li>
              ))}
            </ul>
          </div>
        );
      case 'analysis':
        if (!aiAnalysisData) return null;
        return (
          <div className="thinking-bubble card" style={thinkingBubbleStyle}>
            <h2 className="thinking-subtitle">Analyzing Questions</h2>
            <ul className="analysis-list">
              {aiAnalysisData.analysis.slice(0, revealedItemCount).map((item: AnalysisItem, index) => (
                <li key={`analysis-${index}`} className="analysis-item" style={{ maxWidth: '100%', overflowX: 'auto' }}>
                  <p className="analysis-question" style={commonTextStyle}><strong>Question:</strong> {item.question}</p>
                  {item.analysis_content && item.analysis_content.trim() !== '' && (
                     <p className="analysis-answer" style={commonTextStyle}>{item.analysis_content}</p>
                  )}
                </li>
              ))}
            </ul>
          </div>
        );
      case 'synthesis':
        if (!aiAnalysisData) return null;
        return (
          <div className="thinking-bubble card" style={thinkingBubbleStyle}>
            <h2 className="thinking-subtitle">Synthesizing Insights</h2>
            <ul className="synthesis-list">
              {aiAnalysisData.synthesis.slice(0, revealedItemCount).map((point, index) => (
                <li key={`synthesis-${index}`} className="synthesis-point" style={commonTextStyle}>{point}</li>
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