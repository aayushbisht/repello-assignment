import re
import logging

logger = logging.getLogger(__name__)

# Common constants for safety and refusal messages
DISALLOWED_OUTPUT_PATTERNS = [
    re.compile(r"kill yourself", re.IGNORECASE),
    re.compile(r"I hate all [a-zA-Z\s]+ people", re.IGNORECASE),
    re.compile(r"how to make a (bomb|explosive|weapon)", re.IGNORECASE),
    re.compile(r"detailed instructions for (fraud|theft|illegal act)", re.IGNORECASE),
    # Add more patterns for NSFW, graphic violence, self-harm encouragement etc.
]

OUTPUT_MODERATED_MESSAGE = "[This content has been moderated due to policy reasons]"

# This specific text is for models (like Mistral) that will be instructed to output *only* this.
# Gemini might be instructed to return a more structured refusal.
SIMPLE_REFUSAL_RESPONSE_TEXT = "I cannot reply to that message."

# Constants for Gemini's structured refusal (if different)
GEMINI_REFUSAL_SUBQUESTION = "Query not processed due to content policy."
GEMINI_REFUSAL_ANALYSIS_QUESTION = "Query refused"
GEMINI_REFUSAL_ANALYSIS_CONTENT = "The user's query violates content policies or requests harmful information."
GEMINI_REFUSAL_SYNTHESIS = "Refused query."
GEMINI_REFUSAL_FINAL_ANSWER = "I am unable to process this request due to content policies."

def moderate_text(text: str) -> str:
    """
    Checks text against disallowed patterns and returns a placeholder if a match is found.
    """
    if not text:
        return ""
    for pattern in DISALLOWED_OUTPUT_PATTERNS:
        if pattern.search(text):
            logger.warning(f"Output text matched disallowed pattern: '{pattern.pattern}'. Text snippet: '{text[:100]}...'")
            return OUTPUT_MODERATED_MESSAGE
    return text 