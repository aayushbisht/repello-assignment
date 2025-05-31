"use client";

import React from 'react';
import { AiResponse } from '../types';

interface FinalAnswerDisplayProps {
  aiAnalysisData: AiResponse | null;
}

const FinalAnswerDisplay: React.FC<FinalAnswerDisplayProps> = ({ aiAnalysisData }) => {
  if (!aiAnalysisData) return null;

  const { final_answer, sources } = aiAnalysisData;

  const parseSourceUrl = (sourceString: string): string => {
    if (!sourceString) return '';
    let foundUrl = '';
    const httpRegex = /https?:\/\/?([^\s"'<>`\\]+)/i;
    let match = sourceString.match(httpRegex);
    if (match && match[0]) {
      foundUrl = match[0];
      if (foundUrl.startsWith("http:/") && !foundUrl.startsWith("http://")) {
        foundUrl = "http://" + foundUrl.substring(6);
      } else if (foundUrl.startsWith("https:/") && !foundUrl.startsWith("https://")) {
        foundUrl = "https://" + foundUrl.substring(7);
      }
    } else {
      const wwwRegex = /(?:^|\s)(www\.[^\s"'<>`\\]+\.[^\s"'<>`\\]+)/i;
      match = sourceString.match(wwwRegex);
      if (match && match[1]) {
        foundUrl = "http://" + match[1];
      }
    }
    if (!foundUrl) {
      console.warn(`No valid URL found in source string: "${sourceString}"`);
      return '';
    }
    return foundUrl.trim();
  };

  const formatAnswerWithLinkedSources = (answerText: string, allSources: string[]): string => {
    if (!answerText) return '';

    // Regex to find [Source N], [Source N, M], [Source N,M,P] etc.
    return answerText.replace(/\[Source\s*([\d\s,]+)\]/g, (match, sourceNumbersStr) => {
      const sourceNumbers = sourceNumbersStr.split(',').map((numStr: string) => parseInt(numStr.trim(), 10));
      
      const links = sourceNumbers.map((num: number) => {
        if (num > 0 && num <= allSources.length) {
          const url = parseSourceUrl(allSources[num - 1]);
          if (url) {
            return `<a href="${url}" target="_blank" rel="noopener noreferrer" class="source-link" title="${allSources[num - 1]}">[${num}]</a>`;
          }
        }
        return `[Source ${num}]`; // Fallback if source/URL not found
      }).join(' ');
      
      return links || match; // Return generated links or original match if no links were made
    });
  };

  return (
    <div className="final-answer-container card">
      <h2 className="final-answer-title">Comprehensive Answer</h2>
      {final_answer.length > 0 ? (
        <ul className="final-answer-list">
          {final_answer.map((item, index) => {
            const formattedItem = formatAnswerWithLinkedSources(item, sources || []);
            return (
              <li 
                key={`final-answer-${index}`} 
                className="final-answer-item"
                dangerouslySetInnerHTML={{ __html: formattedItem }}
              />
            );
          })}
        </ul>
      ) : (
        <p>No final answer provided.</p>
      )}
      
      {/* Keep additional sources section if AI might provide sources not directly cited in final_answer */}
      {sources && sources.length > 0 && (
        <div className="additional-sources-container">
          <h3 className="additional-sources-title">All Provided Sources:</h3>
          <ul className="additional-sources-list">
            {sources.map((source, idx) => {
              const sourceUrl = parseSourceUrl(source);
              if (!sourceUrl) return null; 

              return (
                <li key={`additional-source-${idx}`} className="additional-source-item">
                  <a 
                    href={sourceUrl}
                    target="_blank" 
                    rel="noopener noreferrer"
                    title={source}
                  >
                    {`[${idx + 1}] ${source.length > 70 ? source.substring(0, 67) + '...' : source}`}
                  </a>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
};

export default FinalAnswerDisplay; 