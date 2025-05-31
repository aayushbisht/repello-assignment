import os
import google.generativeai as genai
from dotenv import load_dotenv
import logging

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
        
        # Construct the prompt with clear instructions for citation
        prompt = f"""You are an AI research assistant. Analyze the following search results and provide a comprehensive answer to the query. Always cite your sources using the format [Source X] where X is the source number.

Query: {query}

Search Results:
{context}

Please provide your response in the following EXACT format:

1. ANALYSIS:
- Step 1: [Your first analysis step with citations]
- Step 2: [Your second analysis step with citations]
- Step 3: [Your third analysis step with citations]

2. SYNTHESIS:
- Key Point 1: [First key finding with citation, e.g., "According to [Source 1], ..."]
- Key Point 2: [Second key finding with citation]
- Key Point 3: [Third key finding with citation]

3. FINAL ANSWER:
[Your comprehensive answer synthesizing all findings, with citations]

4. SOURCES:
[List of sources used with their URLs]

Important:
- Always cite sources using [Source X] format
- Include at least one citation for each key point
- Ensure your response is factual and well-supported by the sources
- If information is from multiple sources, cite all relevant sources"""

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
            "analysis": [],
            "synthesis": [],
            "final_answer": "",
            "sources": []
        }
        
        # Split into major sections
        sections = response_text.split('\n\n')
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
                
            # Process each section based on its header
            if section.startswith('1. ANALYSIS:'):
                # Extract analysis steps
                steps = section.split('\n')[1:]  # Skip the header
                for step in steps:
                    if step.startswith('- Step'):
                        structured_response["analysis"].append(step[step.find(':')+1:].strip())
                        
            elif section.startswith('2. SYNTHESIS:'):
                # Extract key points
                points = section.split('\n')[1:]  # Skip the header
                for point in points:
                    if point.startswith('- Key Point'):
                        structured_response["synthesis"].append(point[point.find(':')+1:].strip())
                        
            elif section.startswith('3. FINAL ANSWER:'):
                # Extract final answer
                answer = section.split('\n', 1)[1]  # Skip the header
                structured_response["final_answer"] = answer.strip()
                
            elif section.startswith('4. SOURCES:'):
                # Extract sources
                sources = section.split('\n')[1:]  # Skip the header
                for source in sources:
                    if source.strip():
                        structured_response["sources"].append(source.strip())
        
        # Validate the response
        if not any(structured_response.values()):
            logger.error("Failed to parse response into structured format")
            return {
                "query": query,
                "reasoning": ["Raw response parsing failed"],
                "key_points": [],
                "answer": response_text,
                "sources": []
            }
        
        return {
            "query": query,
            "reasoning": structured_response["analysis"],
            "key_points": structured_response["synthesis"],
            "answer": structured_response["final_answer"],
            "sources": structured_response["sources"]
        }
        
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