import httpx
import json
import logging
import os

logger = logging.getLogger(__name__)

# It is assumed that Ollama is running on localhost:11434
# The user can set OLLAMA_BASE_URL in .env if it's different
OLLAMA_API_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_GENERATE_ENDPOINT = f"{OLLAMA_API_BASE_URL}/api/generate"

DEFAULT_OLLAMA_TIMEOUT = 120  # seconds

async def generate_ollama_raw_response(model_name: str, prompt: str, system_message: str = None) -> str:
    """
    Generates a raw text response from a local Ollama model.

    Args:
        model_name (str): The name of the Ollama model to use (e.g., "mistral").
        prompt (str): The user's prompt.
        system_message (str, optional): An optional system message for the model.

    Returns:
        str: The full response text from the model, or an error message string starting with "Error:".
    """
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,  # Get the full response at once for simplicity.
    }
    if system_message:
        payload["system"] = system_message

    logger.info(f"Sending request to Ollama model '{model_name}' at {OLLAMA_GENERATE_ENDPOINT}. Prompt (first 100 chars): '{prompt[:100]}...'")

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_OLLAMA_TIMEOUT) as client:
            response = await client.post(OLLAMA_GENERATE_ENDPOINT, json=payload)
            response.raise_for_status() 

            response_data = response.json()
            
            if "response" in response_data and isinstance(response_data["response"], str):
                full_response = response_data["response"].strip()
                logger.info(f"Received response from Ollama model '{model_name}'. Length: {len(full_response)}. Response (first 100 chars): '{full_response[:100]}...'")
                return full_response
            elif "error" in response_data:
                error_msg = response_data['error']
                logger.error(f"Ollama API returned an error for model '{model_name}': {error_msg}")
                return f"Error: Ollama API error - {error_msg}"
            else:
                logger.error(f"Unexpected response structure from Ollama model '{model_name}': {response_data}")
                return "Error: Unexpected response structure from Ollama."

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error calling Ollama API for model '{model_name}': {e.response.status_code} - {e.response.text}", exc_info=True)
        return f"Error: Ollama API request failed with status {e.response.status_code}. Details: {e.response.text[:100]}"
    except httpx.RequestError as e:
        logger.error(f"Request error calling Ollama API (model '{model_name}') at {OLLAMA_GENERATE_ENDPOINT}: {e}", exc_info=True)
        return f"Error: Could not connect to Ollama API at {OLLAMA_API_BASE_URL}. Ensure Ollama is running and accessible."
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON response from Ollama (model '{model_name}'): {e}", exc_info=True)
        return "Error: Invalid JSON response from Ollama."
    except Exception as e:
        logger.error(f"An unexpected error occurred while calling Ollama model '{model_name}': {str(e)}", exc_info=True)
        return f"Error: An unexpected error occurred with the Ollama model - {str(e)}"

async def check_ollama_model_availability(model_name: str) -> tuple[bool, str]:
    """Checks if a specific model is available in Ollama and provides its details or an error message."""
    logger.info(f"Checking Ollama for model: {model_name}")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{OLLAMA_API_BASE_URL}/api/show", json={"name": model_name})
            if response.status_code == 200:
                details = response.json()
                logger.info(f"Model '{model_name}' is available. Details: {details.get('details', {}).get('family')}")
                return True, f"Model '{model_name}' is available."
            elif response.status_code == 404:
                logger.warning(f"Model '{model_name}' not found in Ollama.")
                return False, f"Error: Model '{model_name}' not found in Ollama. Please ensure you have pulled it (e.g., 'ollama pull {model_name}')."
            else:
                logger.error(f"Error checking model '{model_name}': {response.status_code} - {response.text}")
                return False, f"Error: Could not verify model '{model_name}'. Status: {response.status_code}."
    except httpx.RequestError:
        logger.error(f"Could not connect to Ollama at {OLLAMA_API_BASE_URL} to check model '{model_name}'.")
        return False, f"Error: Could not connect to Ollama to verify model '{model_name}'."
    except Exception as e:
        logger.error(f"Unexpected error checking Ollama model '{model_name}': {e}", exc_info=True)
        return False, f"Error: Unexpected error verifying model '{model_name}'."

# Example usage for testing (can be run directly if needed)
# async def main_test():
#     model_to_test = "mistral" # Or your specific model name
#     available, message = await check_ollama_model_availability(model_to_test)
#     print(message)
#     if available:
#         print(f"\nAttempting to generate text with '{model_to_test}'...")
#         test_prompt = "Explain the concept of an LLM in one sentence."
#         response = await generate_ollama_raw_response(model_name=model_to_test, prompt=test_prompt)
#         print(f"\nResponse from '{model_to_test}':\n{response}")

# if __name__ == "__main__":
#     import asyncio
#     logging.basicConfig(level=logging.INFO) # Ensure logger is configured for standalone run
#     asyncio.run(main_test()) 