"use client";

import React, { useState, useEffect, useCallback } from 'react';
import SearchForm from '../components/SearchForm';
import ThinkingProcessDisplay from '../components/ThinkingProcessDisplay';
import FinalAnswerDisplay from '../components/FinalAnswerDisplay';
import { FetchedLinksResponse, AiResponse, DisplayStage } from '../types';

const HomePage: React.FC = () => {
  const [currentQuery, setCurrentQuery] = useState<string>("");
  const [fetchedLinksData, setFetchedLinksData] = useState<FetchedLinksResponse | null>(null);
  const [aiAnalysisData, setAiAnalysisData] = useState<AiResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false); // General loading for user feedback
  const [error, setError] = useState<string | null>(null);
  const [currentDisplayStage, setCurrentDisplayStage] = useState<DisplayStage>('idle');
  const [currentLinkIndex, setCurrentLinkIndex] = useState<number>(0);
  const [loadingMessage, setLoadingMessage] = useState<string>("");

  const STAGE_DELAY = 1500; 
  const LINK_DISPLAY_DELAY = 700;

  // Function to fetch AI Analysis
  const fetchAiAnalysis = useCallback(async (query: string, linksData: FetchedLinksResponse) => {
    setCurrentDisplayStage('fetchingAiAnalysis');
    setLoadingMessage("Preparing AI analysis...");
    try {
      const response = await fetch(`http://localhost:8000/api/fetch-ai-analysis`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json' 
        },
        body: JSON.stringify({ 
          original_query: query,
          search_results: linksData 
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'AI analysis failed: ' + response.statusText }));
        throw new Error(errorData.detail || 'AI analysis network response was not ok');
      }
      const analysisData: AiResponse = await response.json();
      setAiAnalysisData(analysisData);
      setCurrentDisplayStage('subquestions'); // Start AI response display
    } catch (err: any) {
      console.error("AI Analysis fetch error:", err);
      setError(err.message || 'An error occurred while fetching AI analysis.');
      setCurrentDisplayStage('error');
    }
  }, []);

  useEffect(() => {
    let timer: NodeJS.Timeout;

    if (currentDisplayStage === 'idle' || currentDisplayStage === 'error' || currentDisplayStage === 'fetchingLinks' || currentDisplayStage === 'fetchingAiAnalysis') {
        // No automatic advancement for these stages from here
        return;
    }

    const advanceStage = () => {
      switch (currentDisplayStage) {
        case 'gatheringLinks':
          if (fetchedLinksData && fetchedLinksData.results.length > 0) {
            if (currentLinkIndex < fetchedLinksData.results.length - 1) {
              timer = setTimeout(() => setCurrentLinkIndex(prev => prev + 1), LINK_DISPLAY_DELAY);
            } else {
              // All links shown, trigger AI analysis fetch
              if (currentQuery && fetchedLinksData) {
                fetchAiAnalysis(currentQuery, fetchedLinksData);
              }
            }
          } else {
          
             if (currentQuery && fetchedLinksData) { // fetchedLinksData would be non-null but results array empty
                fetchAiAnalysis(currentQuery, fetchedLinksData);
            }
          }
          break;
        case 'subquestions':
          if (aiAnalysisData) {
            timer = setTimeout(() => setCurrentDisplayStage('analysis'), STAGE_DELAY);
          }
          break;
        case 'analysis':
          if (aiAnalysisData) {
            timer = setTimeout(() => setCurrentDisplayStage('synthesis'), STAGE_DELAY);
          }
          break;
        case 'synthesis':
          if (aiAnalysisData) {
            timer = setTimeout(() => setCurrentDisplayStage('final'), STAGE_DELAY);
          }
          break;
        default:
          break;
      }
    };

    advanceStage();
    return () => clearTimeout(timer);
  }, [currentDisplayStage, fetchedLinksData, aiAnalysisData, currentLinkIndex, fetchAiAnalysis, currentQuery]);

  const handleSearch = async (searchQuery: string) => {
    setCurrentQuery(searchQuery);
    setIsLoading(true);
    setError(null);
    setFetchedLinksData(null);
    setAiAnalysisData(null);
    setCurrentLinkIndex(0);
    setCurrentDisplayStage('fetchingLinks');
    setLoadingMessage("Fetching relevant links...");

    try {
      const response = await fetch(`http://localhost:8000/api/fetch-links`, {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        body: JSON.stringify({ query: searchQuery }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Link fetch failed: ' + response.statusText }));
        throw new Error(errorData.detail || 'Link fetch network response was not ok');
      }
      const linksData: FetchedLinksResponse = await response.json();
      setFetchedLinksData(linksData);

      if (linksData && linksData.results && linksData.results.length > 0) {
        setCurrentDisplayStage('gatheringLinks');
      } else {
        
        setLoadingMessage("No specific links found. Attempting general analysis...")
        
        const emptyLinksData: FetchedLinksResponse = { query: searchQuery, results: [], total_results: 0 };
        fetchAiAnalysis(searchQuery, emptyLinksData);
      }
    } catch (err: any) {
      console.error("Search error:", err);
      setError(err.message || 'An unknown error occurred during search.');
      setCurrentDisplayStage('error');
    } finally {
      setIsLoading(false); 
                        
    }
  };
  
  // Determine which data to pass to ThinkingProcessDisplay
  const thinkingAiData = (currentDisplayStage === 'subquestions' || currentDisplayStage === 'analysis' || currentDisplayStage === 'synthesis') 
                       ? aiAnalysisData 
                       : null;
  const thinkingLinksData = (currentDisplayStage === 'gatheringLinks') 
                          ? fetchedLinksData 
                          : null;

  return (
    <div className="container">
      <h1>AI Research Assistant</h1>
      <SearchForm onSearch={handleSearch} isLoading={isLoading || currentDisplayStage === 'fetchingLinks' || currentDisplayStage === 'fetchingAiAnalysis'} />

      {(currentDisplayStage === 'fetchingLinks' || currentDisplayStage === 'fetchingAiAnalysis') && 
        <ThinkingProcessDisplay 
            fetchedLinksData={null}
            aiAnalysisData={null} 
            displayStage={currentDisplayStage} 
            loadingMessage={loadingMessage}
        />
      }

      {currentDisplayStage === 'gatheringLinks' && fetchedLinksData && 
        <ThinkingProcessDisplay 
            fetchedLinksData={fetchedLinksData}
            aiAnalysisData={null} 
            displayStage={currentDisplayStage} 
            currentLinkIndex={currentLinkIndex}
        />
      }

      {(currentDisplayStage === 'subquestions' || currentDisplayStage === 'analysis' || currentDisplayStage === 'synthesis') && aiAnalysisData &&
         <ThinkingProcessDisplay 
            fetchedLinksData={null}
            aiAnalysisData={aiAnalysisData} 
            displayStage={currentDisplayStage} 
        />
      }

      {currentDisplayStage === 'final' && aiAnalysisData && (
        <FinalAnswerDisplay aiAnalysisData={aiAnalysisData} />
      )}

      {currentDisplayStage === 'error' && error && 
        <p className="error-message">Error: {error}</p>
      }
    </div>
  );
};

export default HomePage; 