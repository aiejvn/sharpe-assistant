from dotenv import load_dotenv
import os
import cohere

class CohereTool:
    def __init__(self, streaming=False):
        load_dotenv()
        self.cohere_client = cohere.ClientV2(os.getenv("COHERE_API_KEY"))
        
    def cohere_response(self, convo:list)->str:
        """
            Given a pre-existing conversation, get Cohere output.
            \nAssumes you have already appended a new message to the convo with user input.
                (should be used if no search is required)
        """
        
        response = self.cohere_client.chat(
            model="command-a-03-2025", 
            messages=convo
        )
        response_text = response.message.content[0].text
        
        return response_text    
