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
      // console.warn(`No valid URL found in source string: "${sourceString}"`); // Less noisy console
      return '';
    }
    return foundUrl.trim();
  };

  const formatAnswerWithLinkedSources = (answerText: string, allSources: string[]): string => {
    if (!answerText) return '';

    // Step 1: Find the entire [Source ...] block
    // Updated regex to be case-insensitive and handle "Source" or "Sources"
    return answerText.replace(/\[(?:Source|Sources)[^\]]+\]/gi, (matchedBlock) => {
      // Step 2: Extract all numbers from within the matchedBlock
      const numbersInBlock = matchedBlock.match(/\d+/g);

      if (!numbersInBlock) {
        return ''; // If no numbers found in the block, remove the block
      }

      const links = numbersInBlock
        .map((numStr: string) => parseInt(numStr, 10))
        .filter((num: number): num is number => !isNaN(num) && num > 0 && num <= allSources.length)
        .map((num: number) => {
          const url = parseSourceUrl(allSources[num - 1]);
          if (url) {
            return `<a href="${url}" target="_blank" rel="noopener noreferrer" class="source-link" title="${allSources[num - 1]}">[${num}]</a>`;
          }
          return `[${num}]`; // Fallback if URL not parsable for a valid source number
        }).join(''); // Join with empty string for [1][2] style
      
      // Return the links directly, preserving original spacing.
      // If links is an empty string (e.g., no valid source numbers found), this effectively removes the matchedBlock.
      return links; 
    });
  };

  return (
    <div className="final-answer-container card">
      <h2 className="final-answer-title">Result</h2>
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