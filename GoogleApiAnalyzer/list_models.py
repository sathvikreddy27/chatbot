import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure the Gemini API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("GEMINI_API_KEY is not set in environment variables!")
    exit(1)

# Configure the generative AI
genai.configure(api_key=GEMINI_API_KEY)

# List available models
print("Listing available models:")
for model in genai.list_models():
    print(f"- {model.name}")
    print(f"  Supported generation methods: {model.supported_generation_methods}")
    print()