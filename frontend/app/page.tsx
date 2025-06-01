"use client";

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { supabase } from '../lib/supabaseClient';
import SearchForm from '../components/SearchForm';
import ThinkingProcessDisplay from '../components/ThinkingProcessDisplay';
import FinalAnswerDisplay from '../components/FinalAnswerDisplay';
import { FetchedLinksResponse, AiResponse, DisplayStage, ChatMessage, ChatSession } from '../types';
import type { User } from '@supabase/supabase-js';

const SESSION_NAME_MAX_LENGTH = 35;
const DEFAULT_NEW_CHAT_NAME = "New Chat";

const HomePage: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoadingAuth, setIsLoadingAuth] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [chatSessionsList, setChatSessionsList] = useState<ChatSession[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState<boolean>(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState<boolean>(false);
  const [currentPendingMessageId, setCurrentPendingMessageId] = useState<string | null>(null);

  const [currentQuery, setCurrentQuery] = useState<string>("");
  const [fetchedLinksData, setFetchedLinksData] = useState<FetchedLinksResponse | null>(null);
  const [aiAnalysisData, setAiAnalysisData] = useState<AiResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [currentDisplayStage, setCurrentDisplayStage] = useState<DisplayStage>('idle');
  const [currentLinkIndex, setCurrentLinkIndex] = useState<number>(0);
  const [loadingMessage, setLoadingMessage] = useState<string>("");
  const [selectedAiModel, setSelectedAiModel] = useState<string>('gemini');

  const chatContainerRef = useRef<HTMLDivElement>(null);
  const prevChatHistoryLengthRef = useRef<number>(0); // Ref to track previous chat history length

  const STAGE_DELAY = 11000;
  const LINK_DISPLAY_DELAY = 700;

  // ---- Supabase Helper Functions ----
  const fetchChatSessions = useCallback(async () => {
    if (!user) return;
    setIsLoadingSessions(true);
    try {
      const { data, error } = await supabase
        .from('chat_sessions')
        .select('id, user_id, created_at, session_name')
        .eq('user_id', user.id)
        .order('created_at', { ascending: false });
      if (error) throw error;
      setChatSessionsList(data || []);
      if (data && data.length > 0 && !currentSessionId) {
        // If no session is active, load the most recent one
        // await handleSelectChat(data[0].id);
      }
    } catch (err: any) {
      console.error("Error fetching chat sessions:", err);
      setError("Could not load chat sessions.");
    }
    setIsLoadingSessions(false);
  }, [user, currentSessionId]);

  const handleNewChat = async () => {
    if (!user) return;
    setChatHistory([]);
    setAiAnalysisData(null);
    setFetchedLinksData(null);
    setCurrentDisplayStage('idle');
    setError(null);
    setCurrentQuery("");
    setIsLoading(false);
    setCurrentPendingMessageId(null);
    setCurrentSessionId(null); 
    prevChatHistoryLengthRef.current = 0; 
    
    try {
      const { data, error } = await supabase
        .from('chat_sessions')
        .insert({ user_id: user.id, session_name: DEFAULT_NEW_CHAT_NAME }) // Use default name
        .select('id, user_id, created_at, session_name')
        .single(); 
      if (error) throw error;
      if (data) {
        setCurrentSessionId(data.id);
        setChatSessionsList(prev => [data, ...prev]);
      }
    } catch (err:any) {
      console.error("Error creating new chat session:", err);
      setError("Could not start a new chat.");
    }
  };

  const handleSelectChat = async (sessionId: string) => {
    if (!user || sessionId === currentSessionId) return;
    setCurrentSessionId(sessionId);
    setChatHistory([]);
    setAiAnalysisData(null);
    setFetchedLinksData(null);
    setCurrentDisplayStage('idle');
    setError(null);
    setCurrentPendingMessageId(null);
    setIsLoadingMessages(true);
    prevChatHistoryLengthRef.current = 0; // Reset for selected chat scroll

    try {
      const { data, error } = await supabase
        .from('chat_messages')
        .select('id, query_text, response_data, created_at, session_id, user_id') // Ensure all needed fields
        .eq('session_id', sessionId)
        .order('created_at', { ascending: true });
      if (error) throw error;
      
      const loadedMessages: ChatMessage[] = (data || []).map(msg => ({
        id: msg.id,
        query: msg.query_text,
        response: msg.response_data as AiResponse | null,
        stage: 'final', 
        created_at: msg.created_at,
        session_id: msg.session_id,
        user_id: msg.user_id,
        // fetchedLinks and error are not directly stored in response_data, so they'll be null/undefined here
      }));
      setChatHistory(loadedMessages);
      prevChatHistoryLengthRef.current = loadedMessages.length; // Set after loading messages
    } catch (err: any) {
      console.error("Error fetching messages for session:", err);
      setError("Could not load messages for this chat.");
    }
    setIsLoadingMessages(false);
  };

  const saveChatMessage = async (messageData: Partial<ChatMessage>, forMessageId?: string | null) => {
    if (!user || !currentSessionId) {
        console.warn("User or session ID missing, cannot save message");
        return null;
    }
    const messageIdToSaveAgainst = forMessageId || currentPendingMessageId;

    const payload: any = {
        session_id: currentSessionId,
        user_id: user.id,
    };
    if (messageData.query) payload.query_text = messageData.query;
    if (messageData.response) payload.response_data = messageData.response;
    // If you add an error_text column to your chat_messages table, uncomment and use this
    // if (messageData.error) payload.error_text = messageData.error;

    if (messageIdToSaveAgainst && !payload.query_text) { // Check if it's an update (no new query_text)
        // This is an update to an existing message (e.g., adding response or error)
        const updatePayload: any = {};
        if (payload.response_data) updatePayload.response_data = payload.response_data;
        // if (payload.error_text) updatePayload.error_text = payload.error_text; // For error saving

        if (Object.keys(updatePayload).length === 0) {
            console.warn("SaveChatMessage called for update without new data.");
            return null; // Or return the existing message if needed
        }

        const { data, error } = await supabase
            .from('chat_messages')
            .update(updatePayload)
            .eq('id', messageIdToSaveAgainst)
            .select('id, query_text, response_data, created_at, session_id, user_id') // Add error_text if used
            .single();
        if (error) {
            console.error("Error updating chat message:", error);
            // Avoid setting global error for this, as it might be a background save
            return null;
        }
        return data;
    } else if (payload.query_text) {
        // This is an insert for a new message (must have query_text)
        const { data, error } = await supabase
            .from('chat_messages')
            .insert(payload) // query_text is definitely in payload here
            .select('id, query_text, response_data, created_at, session_id, user_id') // Add error_text if used
            .single();
        if (error) {
            console.error("Error saving new chat message:", error);
            return null;
        }
        return data; 
    } else {
        console.warn("saveChatMessage called without query for new message or update data for existing.");
        return null;
    }
  };

  // ---- Auth and Initial Load ----
  useEffect(() => {
    const checkUserAndLoadData = async () => {
      const { data: { session }, error: sessionError } = await supabase.auth.getSession();
      if (sessionError) {
        console.error("Error getting session:", sessionError);
        setIsLoadingAuth(false); router.push('/login'); return;
      }
      if (session?.user) {
        setUser(session.user);
        setIsLoadingSessions(true);
        try {
          const { data: sessionsData, error: sessionsError } = await supabase
            .from('chat_sessions')
            .select('id, user_id, created_at, session_name')
            .eq('user_id', session.user.id)
            .order('created_at', { ascending: false });
          if (sessionsError) throw sessionsError;
          const validSessions = sessionsData || [];
          setChatSessionsList(validSessions);
          if (validSessions.length > 0) {
            await handleSelectChat(validSessions[0].id);
          } else {
            // Option: await handleNewChat(); // Create a new chat if none exist on first login
          }
        } catch (err: any) {
          console.error("Error fetching initial chat sessions:", err);
          setError("Could not load initial chat sessions.");
        }
        setIsLoadingSessions(false);
      } else {
        router.push('/login');
      }
      setIsLoadingAuth(false);
    };
    checkUserAndLoadData();

    const { data: authListener } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_OUT') {
        setUser(null); setChatHistory([]); setChatSessionsList([]); setCurrentSessionId(null); setCurrentPendingMessageId(null); router.push('/login');
      } else if ((event === 'SIGNED_IN' || event === 'USER_UPDATED') && session?.user) {
        setUser(session.user);
        if (pathname === '/login') router.push('/');
        else if (!isLoadingAuth && chatSessionsList.length === 0 && !currentSessionId) fetchChatSessions();
      }
    });
    return () => { authListener.subscription.unsubscribe(); };
  }, [router, pathname, isLoadingAuth]); // Removed fetchChatSessions and handleSelectChat from deps

  // Scroll to bottom effect
  useEffect(() => {
    if (chatContainerRef.current) {
      const hasNewMessage = chatHistory.length > prevChatHistoryLengthRef.current;
      const isAiProcessing = !!currentPendingMessageId;

      // Scroll to bottom if a new message is added OR if AI is actively processing the current query
      if (hasNewMessage || isAiProcessing) {
        chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
      }
    }
    // Update the ref to the current length for the next comparison
    prevChatHistoryLengthRef.current = chatHistory.length;
  }, [chatHistory, currentPendingMessageId]); // Depend on chatHistory and currentPendingMessageId

  // ---- Core Chat Logic ----
  const fetchAiAnalysis = useCallback(async (query: string, linksData: FetchedLinksResponse, forMessageId: string | null) => {
    setAiAnalysisData(null); // Clear previous global AI data
    setCurrentDisplayStage('fetchingAiAnalysis');
    setLoadingMessage("Preparing AI analysis...");
    setError(null);
    try {
      // Determine endpoint based on selectedAiModel
      const aiEndpoint = selectedAiModel === 'mistral'
        ? `http://localhost:8000/api/fetch-mistral-analysis`
        : `http://localhost:8000/api/fetch-ai-analysis`;

      console.log(`Fetching AI analysis from: ${aiEndpoint} for model: ${selectedAiModel}`);

      const response = await fetch(aiEndpoint, { // <-- Use dynamic endpoint
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ original_query: query, search_results: linksData }),
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'AI analysis failed: ' + response.statusText }));
        throw new Error(errorData.detail || 'AI analysis network response was not ok');
      }
      const analysisRespData: AiResponse = await response.json();
      setAiAnalysisData(analysisRespData); // Set global for ThinkingProcessDisplay
      setCurrentDisplayStage('subquestions'); // Start thinking animation

      await saveChatMessage({ response: analysisRespData }, forMessageId);
      // Update local chat history, but keep its stage based on global currentDisplayStage until 'final'
      setChatHistory(prev => prev.map(ch => 
        ch.id === forMessageId ? { ...ch, response: analysisRespData } : ch
      ));

    } catch (err: any) {
      console.error("AI Analysis fetch error:", err);
      const errorMsg = err.message || 'An error occurred while fetching AI analysis.';
      setError(errorMsg);
      setCurrentDisplayStage('error');
      await saveChatMessage({ error: errorMsg }, forMessageId); 
      setChatHistory(prev => prev.map(ch => 
        ch.id === forMessageId ? { ...ch, error: errorMsg, stage: 'error' } : ch
      ));
      setCurrentPendingMessageId(null); // Error ends pending state
    }
  }, [user, currentSessionId, selectedAiModel]);

  // Stage advancement logic for an active query
  useEffect(() => {
    if (!currentPendingMessageId || isLoadingAuth || currentDisplayStage === 'idle' || currentDisplayStage === 'error' || currentDisplayStage === 'fetchingLinks' || currentDisplayStage === 'fetchingAiAnalysis') {
      return;
    }
    let timer: NodeJS.Timeout;
    const advanceStage = () => {
      switch (currentDisplayStage) {
        case 'gatheringLinks':
          if (fetchedLinksData && fetchedLinksData.results.length > 0) {
            if (currentLinkIndex < fetchedLinksData.results.length - 1) {
              timer = setTimeout(() => setCurrentLinkIndex(prev => prev + 1), LINK_DISPLAY_DELAY);
            } else {
              if (currentQuery && fetchedLinksData) {
                fetchAiAnalysis(currentQuery, fetchedLinksData, currentPendingMessageId);
              }
            }
          } else {
            if (currentQuery && fetchedLinksData) { 
              fetchAiAnalysis(currentQuery, fetchedLinksData, currentPendingMessageId);
            }
          }
          break;
        case 'subquestions': if (aiAnalysisData) timer = setTimeout(() => setCurrentDisplayStage('analysis'), STAGE_DELAY); break;
        case 'analysis': if (aiAnalysisData) timer = setTimeout(() => setCurrentDisplayStage('synthesis'), STAGE_DELAY); break;
        case 'synthesis': 
          if (aiAnalysisData) {
            timer = setTimeout(() => { 
              setCurrentDisplayStage('final');
              setChatHistory(prev => prev.map(ch => ch.id === currentPendingMessageId ? {...ch, stage: 'final'} : ch));
              setCurrentPendingMessageId(null); // Query processing finished
              setAiAnalysisData(null); // Clear global AI data after use
              setFetchedLinksData(null); // Clear global links data
              setCurrentQuery(""); // Clear current query context
            }, STAGE_DELAY); 
          }
          break;
        default: break;
      }
    };
    advanceStage();
    return () => clearTimeout(timer);
  }, [currentDisplayStage, fetchedLinksData, aiAnalysisData, currentLinkIndex, fetchAiAnalysis, currentQuery, isLoadingAuth, currentPendingMessageId]);

  const handleSearch = async (searchQuery: string) => {
    if (!user) {
      setError("User not authenticated. Please login.");
      return;
    }
    if (!searchQuery.trim()) {
      setError("Search query cannot be empty.");
      return;
    }

    let activeSessionId = currentSessionId;
    let isNewSessionCreatedForThisSearch = false;

    const newSessionName = searchQuery.length > SESSION_NAME_MAX_LENGTH 
                           ? searchQuery.substring(0, SESSION_NAME_MAX_LENGTH - 3) + "..." 
                           : searchQuery;

    if (!activeSessionId) {
        setIsLoading(true); // For session creation
        const { data: newSessionData, error: newSessionError } = await supabase
            .from('chat_sessions')
            .insert({ user_id: user.id, session_name: newSessionName }) // Use query-derived name
            .select('id, user_id, created_at, session_name')
            .single();
        setIsLoading(false);
        if (newSessionError || !newSessionData) {
            console.error("Error creating new session implicitly:", newSessionError);
            setError("Could not start a new chat session."); return;
        }
        activeSessionId = newSessionData.id;
        setCurrentSessionId(activeSessionId);
        setChatSessionsList(prev => [newSessionData, ...prev]);
        setChatHistory([]); 
        prevChatHistoryLengthRef.current = 0;
        isNewSessionCreatedForThisSearch = true;
    }
    
    if (!activeSessionId) { 
        setError("Critical: No active session ID found or created."); return;
    }

    // If this isn't a brand new session created above, 
    // check if it's a default-named session needing an update.
    if (!isNewSessionCreatedForThisSearch) {
        const currentSessionObject = chatSessionsList.find(s => s.id === activeSessionId);
        // Check if the current session has the default name AND has no messages yet.
        // The `chatHistory` check ensures we only rename it on the very first query.
        if (currentSessionObject && currentSessionObject.session_name === DEFAULT_NEW_CHAT_NAME && chatHistory.length === 0) {
             try {
                const { data: updatedSession, error: updateError } = await supabase
                    .from('chat_sessions')
                    .update({ session_name: newSessionName })
                    .eq('id', activeSessionId)
                    .select('id, user_id, created_at, session_name')
                    .single();

                if (updateError) throw updateError;
                if (updatedSession) {
                    setChatSessionsList(prevList => prevList.map(s => 
                        s.id === activeSessionId ? updatedSession : s
                    ));
                }
             } catch (err) {
                console.error("Error updating session name for default chat:", err);
                // Not a critical error to block search, so we just log it.
             }
        }
    }
    
    // Reset global states for the new query processing flow
    setCurrentQuery(searchQuery);
    setIsLoading(true);
    setError(null);
    setFetchedLinksData(null);
    setAiAnalysisData(null);
    setCurrentLinkIndex(0);
    setCurrentDisplayStage('fetchingLinks');
    setLoadingMessage("Fetching relevant links...");
    
    const initialMessageData = { query: searchQuery, stage: 'fetchingLinks' as DisplayStage, session_id: activeSessionId, user_id: user.id };
    const savedQueryRecord = await saveChatMessage(initialMessageData, null); // Pass null for forMessageId to insert

    if (savedQueryRecord && savedQueryRecord.id) {
        setCurrentPendingMessageId(savedQueryRecord.id);
        setChatHistory(prev => [...prev, { ...initialMessageData, id: savedQueryRecord.id, created_at: savedQueryRecord.created_at }]);
    } else {
        setChatHistory(prev => [...prev, { ...initialMessageData, id: `local-${Date.now()}` }]); // Local fallback
        console.error("Failed to save initial query to DB. Proceeding with local history item.");
    }
    
    try {
      const response = await fetch(`http://localhost:8000/api/fetch-links`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ query: searchQuery }),
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Link fetch failed: ' + response.statusText }));
        throw new Error(errorData.detail || 'Link fetch network response was not ok');
      }
      const linksDataResp: FetchedLinksResponse = await response.json();
      setFetchedLinksData(linksDataResp); // Set global for ThinkingProcessDisplay
      
      setChatHistory(prev => prev.map(ch => 
        ch.id === (savedQueryRecord?.id || currentPendingMessageId) ? 
        { ...ch, fetchedLinks: linksDataResp, stage: (linksDataResp?.results?.length > 0) ? 'gatheringLinks' : 'fetchingAiAnalysis' } : ch
      ));

      if (linksDataResp && linksDataResp.results && linksDataResp.results.length > 0) {
        setCurrentDisplayStage('gatheringLinks');
      } else {
        setLoadingMessage("No specific links found. Attempting general analysis...");
        const emptyLinksData: FetchedLinksResponse = { query: searchQuery, results: [], total_results: 0 };
        fetchAiAnalysis(searchQuery, emptyLinksData, savedQueryRecord?.id || currentPendingMessageId);
      }
    } catch (err: any) {
      console.error("Search error:", err);
      const errorMsg = err.message || 'An unknown error occurred during search.';
      setError(errorMsg);
      setCurrentDisplayStage('error');
      if (savedQueryRecord?.id || currentPendingMessageId) {
         await saveChatMessage({ error: errorMsg }, savedQueryRecord?.id || currentPendingMessageId); 
      }
      setChatHistory(prev => prev.map(ch => 
        ch.id === (savedQueryRecord?.id || currentPendingMessageId) ? { ...ch, error: errorMsg, stage: 'error' } : ch
      ));
      setCurrentPendingMessageId(null); // Error ends pending state
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    // Auth listener will redirect
  };

  // ---- Render Logic ----
  if (isLoadingAuth || (!user && pathname !== '/login')) {
    return <div style={{display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', width:'100vw', overflow:'hidden'}}>Loading authentication...</div>;
  }
  if (pathname === '/login') return null;
  if (!user) { 
    router.push('/login');
    return <div style={{display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', width:'100vw', overflow:'hidden'}}>Redirecting to login...</div>; 
  }
  
  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', flexDirection: 'row', overflow: 'hidden' /* Prevent body scroll */ }}>
      {/* Sidebar */}
      <div style={{ width: '280px', backgroundColor: '#f0f2f5', padding: '15px', borderRight: '1px solid #ddd', display: 'flex', flexDirection: 'column', gap: '10px', overflowY: 'auto' /* Allow sidebar to scroll if content overflows */ }}>
        <div style={{display: 'flex', justifyContent:'space-between', alignItems:'center'}}>
            <h2 style={{margin:0}}>Chat History</h2>
            {user && <span style={{fontSize:'0.8em', color:'#555'}}>{user.email?.split('@')[0]}</span>}
        </div>
        <button onClick={handleNewChat} style={{padding: '8px', cursor:'pointer'}} disabled={isLoading || isLoadingSessions || isLoadingMessages}>New Chat</button>
        {isLoadingSessions && <p>Loading sessions...</p>}
        <div style={{flexGrow:1, overflowY: 'auto', border:'1px solid #ccc', borderRadius:'4px', background:'#fff'}}>
          {chatSessionsList.map(session => (
            <div 
              key={session.id} 
              onClick={() => handleSelectChat(session.id)} 
              style={{
                padding: '10px',
                cursor: 'pointer', 
                borderBottom: '1px solid #eee',
                backgroundColor: currentSessionId === session.id ? '#e7f3ff' : 'transparent',
                fontWeight: currentSessionId === session.id ? 'bold' : 'normal',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}
              title={session.session_name || new Date(session.created_at).toLocaleDateString()}
            >
              {session.session_name || new Date(session.created_at).toLocaleDateString()}
            </div>
          ))}
        </div>
        <button onClick={handleLogout} style={{padding: '8px', cursor:'pointer'}}>Logout</button>
      </div>

      {/* Main Content */}
      <div style={{ flexGrow: 1, display: 'flex', flexDirection: 'column', height: '100%',width:'1000px', overflow: 'hidden', marginTop: '10px'  }}>
       
        <div 
          ref={chatContainerRef} 
          className="container" 
          style={{ 
            flexGrow: 1, 
            overflowY: 'auto', 
            overflowX: 'hidden',
            padding: '20px', 
            paddingBottom: '20px' 
          }}
        >
          {!currentSessionId && !isLoadingSessions && !isLoadingMessages && chatSessionsList.length === 0 && (
             <div style={{textAlign: 'center', marginTop: '50px'}}>
                <p>No chats yet. Click "New Chat" to start a conversation.</p>
             </div>
          )}
          {(!currentSessionId && !isLoadingSessions && !isLoadingMessages && chatSessionsList.length > 0 ) && (
             <div style={{textAlign: 'center', marginTop: '50px'}}>
                <p>Select a chat from the sidebar or start a "New Chat".</p>
             </div>
          )}
          {isLoadingMessages && currentSessionId && <p style={{textAlign: 'center', marginTop: '20px'}}>Loading messages...</p>}
          
          {chatHistory.map((chatItem) => (
            <div key={chatItem.id || `local-${chatItem.query}`} style={{ marginBottom: '20px'}}>
              <div style={{fontWeight: 'bold', backgroundColor: '#e0e0e0', padding: '8px 12px', borderRadius: '5px 5px 0 0'}}>Search: {chatItem.query}</div>
              
              {chatItem.id === currentPendingMessageId && 
               (currentDisplayStage === 'fetchingLinks' || currentDisplayStage === 'fetchingAiAnalysis' || 
                currentDisplayStage === 'gatheringLinks' || currentDisplayStage === 'subquestions' || 
                currentDisplayStage === 'analysis' || currentDisplayStage === 'synthesis') && (
                <ThinkingProcessDisplay 
                    fetchedLinksData={fetchedLinksData} 
                    aiAnalysisData={aiAnalysisData} 
                    displayStage={currentDisplayStage} 
                    loadingMessage={loadingMessage} 
                    currentLinkIndex={currentLinkIndex} />
              )}

              {chatItem.response && chatItem.stage === 'final' && 
                <FinalAnswerDisplay aiAnalysisData={chatItem.response} />}
              {chatItem.error && chatItem.stage === 'error' &&
                <p className="error-message" style={{marginTop:0, borderRadius:'0 0 5px 5px'}}>Error: {chatItem.error}</p>}
            </div>
          ))}
        </div>
        
        <div style={{ padding: '15px 20px',marginTop: '-10px', borderTop: '1px solid #ddd', backgroundColor: '#f8f9fa', flexShrink: 0 /* Prevent shrinking */ }}>
          {/* AI Model Selector */}
          <div style={{ marginBottom: '10px', textAlign: 'center' }}>
            <label htmlFor="ai-model-select" style={{ marginRight: '8px', fontSize: '0.9em' }}>Select AI Model: </label>
            <select
              id="ai-model-select"
              value={selectedAiModel}
              onChange={(e) => setSelectedAiModel(e.target.value)}
              disabled={isLoading || currentDisplayStage !== 'idle'} // Disable if busy or not in idle stage
              style={{ padding: '5px', borderRadius: '4px', border: '1px solid #ccc' }}
            >
              <option value="gemini">Gemini (Google)</option>
              <option value="mistral">Mistral (Local)</option>
            </select>
          </div>
          <SearchForm onSearch={handleSearch} isLoading={isLoading || isLoadingSessions || isLoadingMessages || currentDisplayStage === 'fetchingLinks' || currentDisplayStage === 'fetchingAiAnalysis'} />
        </div>
      </div>
    </div>
  );
};

export default HomePage; 