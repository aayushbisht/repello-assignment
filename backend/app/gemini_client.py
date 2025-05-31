import os
import google.generativeai as genai
from dotenv import load_dotenv
import logging
import re

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
    Generate a response using Gemini based on search results.
    
    Args:
        query (str): The user's search query
        search_results (list): List of search results with title, url, and content
        
    Returns:
        dict: Structured response with reasoning steps and final answer
    """
    try:
        # Prepare context from search results with clear source attribution
        context = "\n\n".join([
            f"SOURCE {i+1}:\nTitle: {result['title']}\nURL: {result['url']}\nContent: {result['content']}\n"
            for i, result in enumerate(search_results)
        ])
        
        # Construct the prompt with flexible analysis structure
        prompt = f"""You are an AI research assistant that provides comprehensive analysis. Analyze the following search results and provide a detailed answer to the query. Always cite your sources using the format [Source X] where X is the source number.

Query: {query}

Search Results:
{context}

Please provide your response in the following EXACT format:

1. SUB-QUESTIONS:
- Question 1: [First sub-question to explore]
- Question 2: [Second sub-question to explore]
[Add more sub-questions as needed based on query complexity and details asked, minimum 2]

2. ANALYSIS:
- Step 1: [Analysis of first sub-question with citations]
- Step 2: [Analysis of second sub-question with citations]
[Add more analysis steps as needed, minimum 2 steps]

3. SYNTHESIS:
- Key Point 1: [First key finding with citation, e.g., "According to [Source 1], ..."]
- Key Point 2: [Second key finding with citation]
[Add more key points as needed based on query complexity and details asked, minimum 2 points]

4. FINAL ANSWER:
[Your comprehensive answer synthesizing all findings, with citations.
The final answer MUST be in bullet-point format.
The length and level of detail should be proportional to the query's complexity and the amount of relevant information found.
For complex queries or when more detail is explicitly requested (e.g., "tell me in detail about...", "explain Java"), provide a more detailed and extensive answer.
Use bullet points (-) for main ideas and optionally use indented sub-bullet points (* or +) for further details or examples.

Example:
- Main point 1, covering key aspect A, with [Source X].
- Main point 2, explaining concept B, based on [Source Y].
  * Sub-detail 2.1, elaborating on B.
  * Sub-detail 2.2, providing an example for B, from [Source Z].
- Main point 3, summarizing findings on C.
]

5. SOURCES:
[List of sources used with their URLs]

Important:
- Always cite sources using [Source X] format
- Include at least one citation for each key point in SYNTHESIS
- Ensure your response is factual and well-supported by the sources
- If information is from multiple sources, cite all relevant sources
- Show your reasoning process clearly
- The number of sub-questions, analysis steps, and key points in SYNTHESIS should be proportional to the query's complexity (minimum of 2 for each, more for complex queries).
- The FINAL ANSWER's length and detail should adapt to the query's complexity and information richness. It MUST be in bullet points.
- For complex queries, feel free to add more sub-questions, steps, and points
- The final answer MUST be comprehensive and detailed, especially for:
  * Queries asking for details
  * Broad topic queries
  * Technical explanations
  * Historical context
  * Comparative analysis
  * Practical applications"""

        # Generate response
        response = model.generate_content(prompt)
        
        if not response or not response.text:
            logger.error("Empty response from Gemini")
            raise Exception("Received empty response from Gemini")
            
        # Parse the response into structured format
        response_text = response.text
        logger.info(f"Raw response from Gemini: {response_text[:200]}...")
        
        # Initialize structured response
        structured_response = {
            "sub_questions": [],
            "analysis": [],
            "synthesis": [],
            "final_answer": [],
            "sources": []
        }
        
        # Split into major sections
        sections = response_text.split('\n\n')
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
                
            # Process each section based on its header
            if section.startswith('1. SUB-QUESTIONS:'):
                # Extract sub-questions
                questions = section.split('\n')[1:]  # Skip the header
                for question in questions:
                    if question.startswith('- Question'):
                        structured_response["sub_questions"].append(question[question.find(':')+1:].strip())
                        
            elif section.startswith('2. ANALYSIS:'):
                # Extract analysis steps
                steps = section.split('\n')[1:]  # Skip the header
                current_step = None
                current_content = []
                
                for line in steps:
                    if line.startswith('- Step'):
                        if current_step is not None:
                            structured_response["analysis"].append({
                                "question": current_step,
                                "analysis_content": ' '.join(current_content)
                            })
                        current_step = line[line.find(':')+1:].strip()
                        current_content = []
                    elif current_step is not None:
                        current_content.append(line.strip())
                
                if current_step is not None:
                    structured_response["analysis"].append({
                        "question": current_step,
                        "analysis_content": ' '.join(current_content)
                    })
                    
            elif section.startswith('3. SYNTHESIS:'):
                # Extract synthesis points
                points = section.split('\n')[1:]  # Skip the header
                for point in points:
                    if point.startswith('- Key Point'):
                        structured_response["synthesis"].append(point[point.find(':')+1:].strip())
                        
            elif section.startswith('4. FINAL ANSWER:'):
                # Extract final answer in bullet points
                answer_lines = section.split('\n')[1:]  # Skip the header
                # Filter out empty lines but preserve others as is (to keep indentation for sub-bullets)
                structured_response["final_answer"] = [line for line in answer_lines if line.strip()]
                
            elif section.startswith('5. SOURCES:'):
                # Extract sources
                sources = section.split('\n')[1:]  # Skip the header
                structured_response["sources"] = [source.strip() for source in sources if source.strip()]
        
        return structured_response
            
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        raise Exception(f"Failed to generate response: {str(e)}")

async def process_search_with_ai(query: str, search_results: dict) -> dict:
    """
    Process search results with AI to generate a comprehensive response.
    
    Args:
        query (str): The user's search query
        search_results (dict): Dictionary containing search results with 'results' key
        
    Returns:
        dict: Processed response with AI-generated content
    """
    try:
        # Extract the actual results array from the search_results dictionary
        if isinstance(search_results, dict) and 'results' in search_results:
            results_array = search_results['results']
        else:
            logger.error(f"Invalid search results format: {search_results}")
            raise Exception("Invalid search results format")

        # Format search results for Gemini
        formatted_results = []
        for result in results_array:
            if isinstance(result, dict):
                formatted_result = {
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", "")
                }
                formatted_results.append(formatted_result)
            else:
                logger.warning(f"Skipping invalid result format: {result}")
        
        if not formatted_results:
            logger.error("No valid search results to process")
            raise Exception("No valid search results to process")
            
        # Generate AI response
        ai_response = await generate_response(query, formatted_results)
        
        return {
            "query": query,
            "search_results": search_results,
            "ai_response": ai_response
        }
    except Exception as e:
        logger.error(f"Error processing search with AI: {str(e)}")
        raise Exception(f"Failed to process search with AI: {str(e)}") 