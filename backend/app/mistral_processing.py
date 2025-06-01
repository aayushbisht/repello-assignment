import logging
import os
from .ollama_client import generate_ollama_raw_response, check_ollama_model_availability
from .shared_safety import moderate_text, SIMPLE_REFUSAL_RESPONSE_TEXT

logger = logging.getLogger(__name__)

# Environment variable for the Ollama model name, defaulting to "mistral"
OLLAMA_MODEL_NAME_MISTRAL = os.getenv("OLLAMA_MODEL_NAME_MISTRAL", "mistral")

# Default structured response, especially for errors or refusal
DEFAULT_MISTRAL_RESPONSE = {
    "sub_questions": ["Could not generate sub-questions."],
    "analysis": [],
    "synthesis": ["Could not generate synthesis."],
    "final_answer": [moderate_text("The AI model could not provide a specific answer at this time.")],
    "sources": []
}

REFUSAL_RESPONSE_STRUCTURE = {
    "sub_questions": ["Query not processed due to content policy."],
    "analysis": [],
    "synthesis": ["Content policy violation."],
    "final_answer": [SIMPLE_REFUSAL_RESPONSE_TEXT], # This is the exact message Mistral is asked to return
    "sources": ["N/A"]
}

async def parse_mistral_structured_output(response_text: str, query: str) -> dict:
    """
    Attempts to parse the free-form text from Mistral into the 5-part JSON structure.
    This is a best-effort parsing as Mistral might not perfectly adhere to the format.
    """
    structured_response = {
        "sub_questions": [], "analysis": [], "synthesis": [],
        "final_answer": [], "sources": []
    }
    try:
        sections = response_text.split('\n\n')
        current_section_name = None

        for section_text in sections:
            section_text = section_text.strip()
            if not section_text: continue

            # Identify section headers (case-insensitive for robustness)
            if section_text.lower().startswith('1. sub-questions:'):
                current_section_name = "sub_questions"
                content = section_text.split('\n', 1)[1:] # Get content after header
                if content:
                    questions = content[0].split('\n')
                    structured_response["sub_questions"] = [
                        q[q.find(':')+1:].strip() for q in questions if q.strip().startswith('- Question') or q.strip().startswith('-')
                    ]
            elif section_text.lower().startswith('2. analysis:'):
                current_section_name = "analysis"
                content = section_text.split('\n', 1)[1:]
                if content:
                    steps_text = content[0].split('\n')
                    current_step_q, current_step_c = None, []
                    for line in steps_text:
                        if line.strip().startswith('- Step'):
                            if current_step_q: 
                                structured_response["analysis"].append({"question": current_step_q, "analysis_content": ' '.join(current_step_c).strip()})
                            current_step_q = line[line.find(':')+1:].strip()
                            current_step_c = []
                        elif current_step_q:
                            current_step_c.append(line.strip())
                    if current_step_q: 
                        structured_response["analysis"].append({"question": current_step_q, "analysis_content": ' '.join(current_step_c).strip()})
            elif section_text.lower().startswith('3. synthesis:'):
                current_section_name = "synthesis"
                content = section_text.split('\n', 1)[1:]
                if content:
                    points = content[0].split('\n')
                    structured_response["synthesis"] = [
                        p[p.find(':')+1:].strip() for p in points if p.strip().startswith('- Key Point') or p.strip().startswith('-')
                    ]
            elif section_text.lower().startswith('4. final answer:'):
                current_section_name = "final_answer"
                content = section_text.split('\n', 1)[1:]
                if content:
                    answer_lines = content[0].split('\n')
                    structured_response["final_answer"] = [ans_line for ans_line in answer_lines if ans_line.strip()] # Keep indentation
            elif section_text.lower().startswith('5. sources:'):
                current_section_name = "sources"
                content = section_text.split('\n', 1)[1:]
                if content:
                    sources_lines = content[0].split('\n')
                    structured_response["sources"] = [src_line.strip() for src_line in sources_lines if src_line.strip()]
            elif current_section_name: # If we are inside a known section and it's a continuation line
                # This is a simple continuation, might need more robust handling for multi-paragraph sections
                pass # The current logic processes sections as blocks. More granular appending could be added if needed.

        # Basic validation and fallback for key fields
        if not structured_response.get("final_answer"):
            logger.warning(f"Final answer not parsed from Mistral response for query '{query[:50]}...'. Using full response as fallback.")
            # Fallback: if parsing fails to get a final_answer, use the whole moderated text
            # but since the text might be very long and unformatted, we provide a message instead.
            # A better fallback might be to use the full response_text if it's not too long.
            structured_response["final_answer"] = ["Could not specifically parse out the final answer section from the AI's response."]
        
        if not structured_response.get("sub_questions"):
            structured_response["sub_questions"] = ["No specific sub-questions parsed."]
        if not structured_response.get("analysis"):
            structured_response["analysis"] = [] # Keep as list
        if not structured_response.get("synthesis"):
            structured_response["synthesis"] = ["No specific synthesis points parsed."]
        if not structured_response.get("sources"):
            structured_response["sources"] = ["No specific sources parsed, check search results."]

        return structured_response

    except Exception as e:
        logger.error(f"Error parsing Mistral structured output for query '{query[:50]}...': {str(e)}", exc_info=True)
        # Return a version of default with the full response_text as a final answer, moderated
        return {
            **DEFAULT_MISTRAL_RESPONSE, 
            "final_answer": [moderate_text(f"Error parsing AI response. Raw response: {response_text[:500]}...")]
        }

async def generate_mistral_response(query: str, search_results: list) -> dict:
    """
    Generates a structured response using the local Ollama model (Mistral) with safety.
    Uses the same detailed prompt structure as Gemini.
    """
    try:
        context = "\n\n".join([
            f"SOURCE {i+1}:\nTitle: {result.get('title', 'N/A')}\nURL: {result.get('url', 'N/A')}\nContent: {result.get('content', 'N/A')}"
            for i, result in enumerate(search_results) if isinstance(result, dict)
        ])

        # The detailed prompt, same as Gemini, with specific safety for Mistral
        # Mistral is instructed for a simple string refusal.
        prompt_for_mistral = f"""You are an AI research assistant. Your primary goal is to provide comprehensive, factual, and helpful answers based on the provided search results. You MUST cite sources using [Source X].

Query: {query}

Search Results:
{context if context else "No specific search results provided for this query."}

IMPORTANT SAFETY INSTRUCTION:
If the user's "Query" (stated above) is asking for instructions on illegal activities, promoting hate speech, generating severely harmful content, or is otherwise grossly inappropriate, you MUST NOT provide a direct answer. Instead, you MUST respond ONLY with the exact phrase: "{SIMPLE_REFUSAL_RESPONSE_TEXT}". Do not add any other text before or after this phrase.

If the query is appropriate and answerable using the provided search results, please provide your response in the following EXACT format (ensure all 5 sections are present):

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
        ollama_model_to_use = OLLAMA_MODEL_NAME_MISTRAL
        raw_mistral_response = await generate_ollama_raw_response(ollama_model_to_use, prompt_for_mistral)

        if not raw_mistral_response:
            logger.error(f"Empty response from Ollama model '{ollama_model_to_use}' for query: {query}")
            return {**DEFAULT_MISTRAL_RESPONSE, "final_answer": [moderate_text("AI model returned an empty response.")]}
        
        if raw_mistral_response.startswith("Error:"):
            logger.error(f"Ollama client returned an error: {raw_mistral_response}")
            return {**DEFAULT_MISTRAL_RESPONSE, "final_answer": [moderate_text(f"AI model error: {raw_mistral_response}")]}

        # Check for the exact refusal message
        if raw_mistral_response.strip() == SIMPLE_REFUSAL_RESPONSE_TEXT:
            logger.info(f"Mistral (Ollama) refused inappropriate query as instructed: {query[:50]}...")
            return REFUSAL_RESPONSE_STRUCTURE # No further moderation needed on this specific text

        # If not a refusal, attempt to parse the structured output
        structured_response = await parse_mistral_structured_output(raw_mistral_response, query)
        
        # Moderation is applied to the final answer AFTER parsing attempt
        if isinstance(structured_response.get("final_answer"), list):
            structured_response["final_answer"] = [
                moderate_text(str(ans_part)) for ans_part in structured_response["final_answer"] if ans_part # Ensure not None/empty
            ]
        else:
            structured_response["final_answer"] = [moderate_text(str(structured_response.get("final_answer", "")))]

        # If moderation or parsing resulted in an empty final_answer list, add a placeholder.
        if not structured_response["final_answer"]:
            structured_response["final_answer"] = [moderate_text("AI response was empty or could not be fully processed after moderation.")]

        # Ensure all keys are present for AiResponseModel compatibility (using DEFAULT_MISTRAL_RESPONSE keys as reference)
        for key in DEFAULT_MISTRAL_RESPONSE.keys():
            if key not in structured_response or not structured_response[key]: # also check if empty list/value for safety
                if key == "analysis": structured_response[key] = [] # Ensure analysis is list
                elif key == "sources" and context: # If sources were provided, list them even if not parsed
                     structured_response[key] = [res.get('url', 'Source URL not available') for res in search_results if isinstance(res, dict)]
                else:
                    structured_response[key] = DEFAULT_MISTRAL_RESPONSE[key]
            elif key == "analysis" and not all(isinstance(item, dict) for item in structured_response.get(key, [])):
                 structured_response[key] = [] # ensure analysis items are dicts or list is empty

        return structured_response

    except Exception as e:
        logger.error(f"Critical error in Mistral generate_response for '{query[:50]}...': {str(e)}", exc_info=True)
        return {**DEFAULT_MISTRAL_RESPONSE, "final_answer": [moderate_text(f"A critical error occurred: {str(e)}")]}

async def process_search_with_mistral(query: str, search_results_data: dict) -> dict:
    """
    Processes search results using the local Mistral (Ollama) AI to generate a response.
    Expected to be called by a FastAPI endpoint.
    """
    try:
        model_name_to_check = OLLAMA_MODEL_NAME_MISTRAL
        # Optional: Check model availability on startup or first call - could be moved to app startup
        # For now, let generate_ollama_raw_response handle model errors if it's not found.
        # available, message = await check_ollama_model_availability(model_name_to_check)
        # if not available:
        #     logger.error(f"Mistral model '{model_name_to_check}' not available: {message}")
        #     return {**DEFAULT_MISTRAL_RESPONSE, "final_answer": [moderate_text(message)]}

        if not isinstance(search_results_data, dict) or 'results' not in search_results_data:
            logger.error(f"Invalid search_results_data format for Mistral AI: {type(search_results_data)}")
            return {**DEFAULT_MISTRAL_RESPONSE, "final_answer": [moderate_text("Invalid search data for AI.")]}

        results_list_for_ai = search_results_data.get('results', [])
        if not isinstance(results_list_for_ai, list):
            logger.warning(f"search_results_data['results'] not a list. Type: {type(results_list_for_ai)}. Using empty list.")
            results_list_for_ai = []
        
        # Ensure content is string for prompt
        cleaned_results_list = []
        for item in results_list_for_ai:
            if isinstance(item, dict):
                item['content'] = str(item.get('content', ''))
                cleaned_results_list.append(item)

        ai_response_content = await generate_mistral_response(query, cleaned_results_list)
        
        # This function returns the dict that AiResponseModel (in main.py) can parse.
        return ai_response_content

    except Exception as e:
        logger.error(f"Critical error in process_search_with_mistral for '{query[:50]}...': {str(e)}", exc_info=True)
        return {**DEFAULT_MISTRAL_RESPONSE, "final_answer": [moderate_text(f"Critical AI processing error with Mistral: {e!s}")]}

# Example for testing (if needed):
# async def main_test_mistral():
#     logging.basicConfig(level=logging.INFO)
#     logger.info(f"Using Mistral model: {OLLAMA_MODEL_NAME_MISTRAL}")
#     available, msg = await check_ollama_model_availability(OLLAMA_MODEL_NAME_MISTRAL)
#     print(msg)
#     if not available:
#         return

#     test_query = "What are the main components of a car engine?"
#     # test_query = "how to make a bomb"
#     sample_search_results = {
#         "results": [
#             {"title": "Car Engine Basics", "url": "http://example.com/engine_basics", "content": "The main components are the engine block, pistons, crankshaft, camshaft, and cylinder head."},
#             {"title": "How Engines Work", "url": "http://example.com/how_engines_work", "content": "Pistons move up and down to turn the crankshaft, which powers the car."}
#         ]
#     }
#     response = await process_search_with_mistral(test_query, sample_search_results)
#     import json
#     print(json.dumps(response, indent=2))

# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(main_test_mistral()) 