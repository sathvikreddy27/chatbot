import os
import logging
import asyncio
import google.generativeai as genai
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure the Gemini API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY is not set in environment variables!")

# Default educational system prompt to focus responses
EDUCATIONAL_SYSTEM_PROMPT = """
You are an educational assistant designed to help users learn and understand various topics. 
Your responses should be:
- Accurate and factual
- Age-appropriate and educational
- Clear and easy to understand
- Focused on teaching and explaining concepts
- Free from personal opinions, biases, or inappropriate content

If asked about topics outside of educational content, politely redirect the conversation 
to educational subjects. If you don't know the answer, acknowledge this 
rather than making up information.
"""

# Configure the generative AI
try:
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Set up the model - using gemini-1.5-flash which is available and supports generateContent
    model = genai.GenerativeModel('gemini-1.5-flash')
    logger.info("Gemini API configured successfully with model: gemini-1.5-flash")
    
except Exception as e:
    logger.error(f"Error configuring Gemini API: {e}")
    model = None

class GeminiChat:
    def __init__(self):
        self.is_initialized = model is not None
    
    def add_message(self, role, content):
        """Add a message to the chat history"""
        # Not needed anymore with the synchronous implementation
        pass
    
    def clear_history(self):
        """Clear the chat history"""
        # We'll create a new chat each time, so no need to clear
        pass
    
    def get_response(self, user_message):
        """Get a response from the Gemini model based on user message and chat history - SYNCHRONOUS version"""
        if not self.is_initialized:
            return {
                "error": "Gemini API is not properly configured. Please check your API key.",
                "success": False
            }
        
        try:
            # Add the system prompt to the user message
            prompt = f"{EDUCATIONAL_SYSTEM_PROMPT}\n\nUser query: {user_message}"
            
            # Use the synchronous API to avoid event loop issues
            response = model.generate_content(prompt)
            
            if response and hasattr(response, 'text'):
                return {
                    "response": response.text,
                    "success": True
                }
            else:
                return {
                    "error": "Failed to get a valid response from Gemini",
                    "success": False
                }
            
        except Exception as e:
            logger.error(f"Error getting response from Gemini: {e}")
            return {
                "error": f"Failed to get a response from the AI assistant. Error: {str(e)}",
                "success": False
            }
