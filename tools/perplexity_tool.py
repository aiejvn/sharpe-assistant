import openai 
from openai import OpenAI
import os
from dotenv import load_dotenv
import io

class PerplexityTool:
    def __init__(self, streaming=False):
        load_dotenv() # Walk up file tree until .env file is found
        self.perplexity_client = OpenAI(
            api_key=os.getenv('PERPLEXITY_API_KEY'), 
            base_url="https://api.perplexity.ai"
        )
    
    def perplexity_response(self, convo:list)->str:
        """
            Given user input words, get perplexity output. 
            \nAssumes you have already appended a new message to the convo with user input.
                (should be used if search is required)
        """
        
        response = self.perplexity_client.chat.completions.create(
            model="sonar-pro",
            messages=convo,
        )
        citations = response.citations
        text = response.choices[0].message.content
                
        return text, citations