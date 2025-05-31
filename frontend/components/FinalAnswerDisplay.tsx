"use client";

import React from 'react';
import { AiResponse } from '../types';

interface FinalAnswerDisplayProps {
  aiAnalysisData: AiResponse | null;
}

const FinalAnswerDisplay: React.FC<FinalAnswerDisplayProps> = ({ aiAnalysisData }) => {
  if (!aiAnalysisData) return null;

  return (
    <div className="final-answer">
      <h2>Final Answer</h2>
      <ul>
        {aiAnalysisData.final_answer.map((item, index) => (
          <li key={`final-answer-${index}`}>{item}</li>
        ))}
      </ul>
      {aiAnalysisData.sources && aiAnalysisData.sources.length > 0 && (
        <div className="sources-list">
          <h3>Sources:</h3>
          <ul>
            {aiAnalysisData.sources.map((source, index) => (
              <li key={`source-${index}`}>
                <a 
                  href={source.startsWith('[Source ') && source.includes(']:') ? source.substring(source.indexOf(']:') + 2).trim() : source}
                  target="_blank" 
                  rel="noopener noreferrer"
                >
                  {source}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default FinalAnswerDisplay; 