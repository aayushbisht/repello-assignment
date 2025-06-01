import os
import google.generativeai as genai
from dotenv import load_dotenv
import logging
import re
from .shared_safety import (
    moderate_text, 
    GEMINI_REFUSAL_SUBQUESTION, 
    GEMINI_REFUSAL_ANALYSIS_CONTENT, 
    GEMINI_REFUSAL_SYNTHESIS, 
    GEMINI_REFUSAL_FINAL_ANSWER,
    GEMINI_REFUSAL_ANALYSIS_QUESTION
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is not set")

genai.configure(api_key=GOOGLE_API_KEY)

# Initialize the model
model = genai.GenerativeModel('gemini-2.0-flash-001')

async def generate_response(query: str, search_results: list) -> dict:
    """
    Generate a response using Gemini based on search results, with safety instructions.
    """
    default_error_response = {
        "sub_questions": ["Error: AI response generation failed."],
        "analysis": [], "synthesis": [],
        "final_answer": [moderate_text("Could not retrieve an answer from the AI model.")], # Moderate default error
        "sources": []
    }
    try:
        context = "\n\n".join([
            f"SOURCE {i+1}:\nTitle: {result.get('title', 'N/A')}\nURL: {result.get('url', 'N/A')}\nContent: {result.get('content', 'N/A')}"
            for i, result in enumerate(search_results) if isinstance(result, dict)
        ])

        prompt = f"""You are an AI research assistant. Your primary goal is to provide comprehensive, factual, and helpful answers based on the provided search results. You MUST cite sources using [Source X].

Query: {query}

Search Results:
{context if context else "No specific search results provided for this query."}

IMPORTANT SAFETY INSTRUCTION:
If the user's "Query" (stated above) is asking for instructions on illegal activities, promoting hate speech, generating severely harmful content, or is otherwise grossly inappropriate, you MUST NOT provide a direct answer. Instead, you MUST respond with the following specific JSON-like structure and nothing else:

1. SUB-QUESTIONS:
- {GEMINI_REFUSAL_SUBQUESTION}
2. ANALYSIS:
- Step 1: {GEMINI_REFUSAL_ANALYSIS_CONTENT}
3. SYNTHESIS:
- Key Point 1: {GEMINI_REFUSAL_SYNTHESIS}
4. FINAL ANSWER:
- {GEMINI_REFUSAL_FINAL_ANSWER}
5. SOURCES:
[N/A]

If the query is appropriate and answerable using the provided search results, please provide your response in the following EXACT format:

1. SUB-QUESTIONS:
- Question 1: [First sub-question to explore]
- Question 2: [Second sub-question to explore]
[Add more sub-questions as needed, minimum 2]

2. ANALYSIS:
- Step 1: [Analysis of first sub-question with citations]
- Step 2: [Analysis of second sub-question with citations]
[Add more analysis steps as needed, minimum 2 steps]

3. SYNTHESIS:
- Key Point 1: [First key finding with citation, e.g., "According to [Source 1], ..."]
- Key Point 2: [Second key finding with citation]
[Add more key points as needed, minimum 2 points]

4. FINAL ANSWER:
[Your comprehensive answer synthesizing all findings, with citations. It MUST be in bullet-point format.]

5. SOURCES:
[List of sources used with their URLs]
"""

        response = model.generate_content(prompt)
        
        if not response or not hasattr(response, 'text') or not response.text:
            logger.error(f"Empty or invalid response from Gemini for query: {query}")
            return default_error_response
            
        response_text = response.text.strip()
        logger.info(f"Gemini raw response for '{query[:50]}...': {response_text[:250]}...")
        
        structured_response = {
            "sub_questions": [], "analysis": [], "synthesis": [],
            "final_answer": [], "sources": []
        }

        # Check for Gemini's structured refusal
        # A simple check: if the specific refusal final answer is present.
        if GEMINI_REFUSAL_FINAL_ANSWER in response_text and GEMINI_REFUSAL_SUBQUESTION in response_text:
            logger.info(f"Gemini indicated query was inappropriate for: {query[:50]}...")
            structured_response["sub_questions"] = [GEMINI_REFUSAL_SUBQUESTION]
            structured_response["analysis"] = [{"question": GEMINI_REFUSAL_ANALYSIS_QUESTION, "analysis_content": GEMINI_REFUSAL_ANALYSIS_CONTENT}]
            structured_response["synthesis"] = [GEMINI_REFUSAL_SYNTHESIS]
            structured_response["final_answer"] = [GEMINI_REFUSAL_FINAL_ANSWER] # Will be moderated below
            structured_response["sources"] = ["N/A"]
        else:
            # Proceed with normal parsing logic (original parsing logic from user file)
            sections = response_text.split('\n\n')
            for section_text in sections:
                section_text = section_text.strip()
                if not section_text: continue

                if section_text.startswith('1. SUB-QUESTIONS:'):
                    questions = section_text.split('\n')[1:]
                    structured_response["sub_questions"] = [q[q.find(':')+1:].strip() for q in questions if q.startswith('- Question')]
                elif section_text.startswith('2. ANALYSIS:'):
                    steps_text = section_text.split('\n')[1:]
                    current_step_q, current_step_c = None, []
                    for line in steps_text:
                        if line.startswith('- Step'):
                            if current_step_q: structured_response["analysis"].append({"question": current_step_q, "analysis_content": ' '.join(current_step_c).strip()})
                            current_step_q = line[line.find(':')+1:].strip()
                            current_step_c = []
                        elif current_step_q: current_step_c.append(line.strip())
                    if current_step_q: structured_response["analysis"].append({"question": current_step_q, "analysis_content": ' '.join(current_step_c).strip()})
                elif section_text.startswith('3. SYNTHESIS:'):
                    points = section_text.split('\n')[1:]
                    structured_response["synthesis"] = [p[p.find(':')+1:].strip() for p in points if p.startswith('- Key Point')]
                elif section_text.startswith('4. FINAL ANSWER:'):
                    answer_lines = section_text.split('\n')[1:]
                    structured_response["final_answer"] = [ans_line for ans_line in answer_lines if ans_line.strip()]
                elif section_text.startswith('5. SOURCES:'):
                    sources_lines = section_text.split('\n')[1:]
                    structured_response["sources"] = [src_line.strip() for src_line in sources_lines if src_line.strip()]
            
            # Basic validation: if final_answer is empty after parsing, put a note.
            if not structured_response.get("final_answer"):
                logger.warning(f"Final answer not parsed from Gemini response for query '{query[:50]}...'")
                structured_response["final_answer"] = ["Could not parse final answer from AI response."]

        # Apply output moderation to all parts of the final answer
        if isinstance(structured_response.get("final_answer"), list):
            structured_response["final_answer"] = [
                moderate_text(str(ans_part)) for ans_part in structured_response["final_answer"] # Ensure ans_part is str
            ]
        else: # Should not happen if logic above is correct, but as a safeguard
             structured_response["final_answer"] = [moderate_text(str(structured_response.get("final_answer", "")))]
        
        # If moderation made final_answer an empty list, add a placeholder
        if not structured_response["final_answer"]:
            structured_response["final_answer"] = [moderate_text("AI response was empty or fully moderated.")]
        
        # Ensure all keys are present for AiResponseModel compatibility
        for key in default_error_response.keys():
            if key not in structured_response:
                structured_response[key] = default_error_response[key]
            elif key == "analysis" and not all(isinstance(item, dict) for item in structured_response.get(key, [])):
                structured_response[key] = [] # ensure analysis is list of dicts or empty

        return structured_response
            
    except Exception as e:
        logger.error(f"Critical error in Gemini generate_response for query '{query[:50]}...': {str(e)}", exc_info=True)
        return default_error_response

async def process_search_with_ai(query: str, search_results: dict) -> dict:
    """
    Process search results with Gemini AI to generate a comprehensive response.
    """
    try:
        if not isinstance(search_results, dict) or 'results' not in search_results:
            logger.error(f"Invalid search results format for Gemini AI: {type(search_results)}")
            return { # Return a structure that AiResponseModel expects
                "sub_questions": ["Error: Invalid search data provided."],
                "analysis": [], "synthesis": [],
                "final_answer": [moderate_text("Cannot process request due to invalid search data.")],
                "sources": []
            }

        results_array = search_results.get('results', [])
        if not isinstance(results_array, list):
            logger.warning(f"search_results['results'] is not a list. Type: {type(results_array)}. Using empty list.")
            results_array = []
        
        # Ensure content within results is string, as expected by Gemini prompt formatting
        formatted_results_for_ai = []
        for res_item in results_array:
            if isinstance(res_item, dict):
                res_item['content'] = str(res_item.get('content', '')) # Ensure content is string
                formatted_results_for_ai.append(res_item)
        
        # Generate AI response using the updated generate_response function
        ai_response_data = await generate_response(query, formatted_results_for_ai)
        
        # main.py expects process_search_with_ai to return the ai_response part for the AiResponseModel
        # The generate_response now returns this directly.
        return ai_response_data 

    except Exception as e:
        logger.error(f"Error processing search with Gemini AI: {str(e)}", exc_info=True)
        return { # Return a structure that AiResponseModel expects
            "sub_questions": ["Error: AI processing failed."],
            "analysis": [], "synthesis": [],
            "final_answer": [moderate_text(f"An error occurred during AI processing: {e!s}")],
            "sources": []
        } 