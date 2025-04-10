import openai 
from openai import OpenAI
import os
from dotenv import load_dotenv
import io
# import cohere
from geopy.geocoders import Photon
from geopy.exc import GeocoderTimedOut

from tools.cohere_tool import CohereTool
from tools.perplexity_tool import PerplexityTool

class BackEnd:
    
    def __init__(self, streaming=False, debug=False):
        load_dotenv()
        
        self.perplexity = PerplexityTool()
        # self.perplexity_client = OpenAI(
        #     api_key=os.getenv('PERPLEXITY_API_KEY'), 
        #     base_url="https://api.perplexity.ai"
        # )
        
        self.openai_client = OpenAI(
            api_key=os.getenv('OPENAI_API_KEY')
        )
        
        self.cohere = CohereTool()
        # self.cohere_client = cohere.ClientV2(os.getenv("COHERE_API_KEY"))
        
        self.convo = [
            {
                "role": "system",
                "content": (
                    "You are Sharpe, an artificial intelligence assistant, and you need to "
                    "engage in a helpful, detailed, polite conversation with a user. "
                    # f"This user lives at {address}. Incorporate this into your search IF AND ONLY IF "
                    f"This user lives near Queen's University, Kingston, Ontario. Incorporate this into your search IF AND ONLY IF the user asks for anything related to location."
                    "Keep responses as brief as possible."
                ),
            },
        ]
        self.streaming = streaming
        self.debug = debug
        
    def audio_to_text(self, audio_file:io.BytesIO)->str:
        audio_file.seek(0) # Reset file pointer to beginning
        
        # IoBytes is not accepted by whisper - .mp3 is
        with open("user_input.mp3", "wb") as f:
            f.write(audio_file.getvalue())
        
        transcription = openai.audio.transcriptions.create(
            model="whisper-1", 
            file=open("./user_input.mp3", "rb"),
        )

        print(transcription.text)
        
        return transcription.text
        
    def text_to_audio(self, text:str)->io.BytesIO:
        """
            Given user input, get a TTS output.
            This is our speed bottleneck - fix this
        """
        response = openai.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="coral",
            input=text
        )
            
        audio_buffer = io.BytesIO(response.content) # Write straight to buffer
        audio_buffer.seek(0)
      
        if self.debug:
            with open("voice_output.mp3", "wb") as f:
                f.write(audio_buffer.getvalue())
      
        return audio_buffer
        
        
    # def cohere_response(self, input_sentence:str)->str:
    #     """
    #         Given user input words, get Cohere output (if no search required)
    #     """
        
    #     self.convo += [{
    #         "role": "user",
    #         "content": (input_sentence),
    #     }]
        
    #     response = self.cohere_client.chat(
    #         model="command-a-03-2025", 
    #         messages=self.convo
    #     )
        
    #     response_text = response.message.content[0].text
        
    #     self.convo += [{
    #         "role":"system",
    #         "content":(response_text)
    #     }]
        
    #     return response_text    

    # def perplexity_response(self, input_sentence:str)->str:
    #     """
    #         Given user input words, get perplexity output (if search required)
    #     """
        
    #     # Special conversation just for search function
    #     self.convo += [{
    #         "role": "user",
    #         "content": (input_sentence),
    #     }]

    #     response = self.perplexity_client.chat.completions.create(
    #         model="sonar-pro",
    #         messages=self.convo,
    #     )
    #     citations = response.citations
    #     text = response.choices[0].message.content
    #     self.convo += [{
    #         "role":"system",
    #         "content":(text)
    #     }]
                
    #     return text, citations

        
    def full_process(self, audio:io.BytesIO)->io.BytesIO:
        transcribed = self.audio_to_text(audio)  
        print("FOUND USER SAID:", transcribed)

        self.convo += [{
            "role": "user",
            "content": (transcribed),
        }]

        if 'today' in transcribed or 'recent' in transcribed:
            text_response = self.perplexity.perplexity_response(self.convo)[0] 
        else:
            text_response = self.cohere.cohere_response(self.convo)
        
        text_response += "Anything else I can help with?" # Ensure we ask the user for more stuff
        
        audio_buffer = self.text_to_audio(text_response)
        
        self.convo += [{
            "role": "system",
            "content": (text_response),
        }]
        
        return audio_buffer
    
    def generate_intro(self)->io.BytesIO:
        """
            Generate the startup audio, if it doesn't exist already.
        """
        response = openai.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="coral",
            input="Hi! I'm Sharpe, your personal hands-free assistant. How may I help you today?"
        )
            
        audio_buffer = io.BytesIO(response.content) # Write straight to buffer
        audio_buffer.seek(0)
      
        return audio_buffer
        
    def get_user_location(self):
        """
            Get the user's location, for more localized requests with perplexity.
        """
        geolocator = Photon(user_agent="measurements")
        
        try:
            location = geolocator.geocode("", exactly_one=True, timeout=10)
            if location:
                address = location.raw.get('address', {})
                return address
            else:
                return "Queen's University, Kingston, Ontario"
                
        except GeocoderTimedOut:
            print("Geocoding services time out")
            return "Queen's University, Kingston, Ontario"
        
if __name__ == "__main__":
    # For a small voice input (4,5,6), this took 12-13 seconds. Can we cut this down? 
        # Update: this is now 9 seconds.
    agent = BackEnd(debug=True)
    # agent.full_process(open("./output.mp3", 'rb'))