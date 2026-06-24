import os
from google import genai
from google.genai import types

class GeminiLLMService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            print("WARNING: GEMINI_API_KEY is missing. LLM capabilities will be mocked or fail.")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

    def generate_explanation(self, prompt: str) -> str:
        if not self.client:
            return "Mock Explanation: [GEMINI_API_KEY missing in .env]. Connect a valid API key to see the actual LLM Project Intelligence output.\n\nPrompt snippet received: " + prompt[:150] + "..."
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            return response.text
        except Exception as e:
            return f"Error interacting with Gemini API: {str(e)}"
