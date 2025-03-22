import openai 
from openai import OpenAI
import os
from dotenv import load_dotenv
import io
import cohere

from audio_configs import CHUNK, CHANNELS, RATE, FORMAT

# If we have time, learn web-sockets to make this stream output in real time.

class AudioAgent:
    
    def __init__(self, streaming=False, debug=False):
        load_dotenv()
        
        self.perplexity_client = OpenAI(
            api_key=os.getenv('PERPLEXITY_API_KEY'), 
            base_url="https://api.perplexity.ai"
        )
        
        self.openai_client = OpenAI(
            api_key=os.getenv('OPENAI_API_KEY')
        )
        
        self.cohere_client = cohere.ClientV2(os.getenv("COHERE_API_KEY"))
        
        self.convo = [
            {
                "role": "system",
                "content": (
                    "You are an artificial intelligence assistant and you need to "
                    "engage in a helpful, detailed, polite conversation with a user."
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
        
        
    def cohere_response(self, input_sentence:str)->str:
        """
            Given user input words, get Cohere output (if no search required)
        """
        
        self.convo += [{
            "role": "user",
            "content": (input_sentence),
        }]
        
        response = self.cohere_client.chat(
            model="command-a-03-2025", 
            messages=self.convo
        )
        
        response_text = response.message.content[0].text
        
        self.convo += [{
            "role":"system",
            "content":(response_text)
        }]
        
        return response_text    

    def perplexity_search(self, input_sentence:str)->str:
        """
            Given user input words, get perplexity output (if search required)
        """
        
        # Special conversation just for search function
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an artificial intelligence assistant and you need to "
                    "engage in a helpful, detailed, polite conversation with a user."
                ),
            },
            {   
                "role": "user",
                "content": (input_sentence),
            },
        ]

        if not self.streaming:
            # chat completion without streaming - defualt for now
            response = self.perplexity_client.chat.completions.create(
                model="sonar-pro",
                messages=messages,
            )
            citations = response.citations
            print(response.choices[0].message.content)
            
            return response, citations
        else:
            # chat completion with streaming - use if needed
            response_stream = self.perplexity_client.chat.completions.create(
                model="sonar-pro",
                messages=messages,
                stream=True,
            )
            citations = response.citations
            
            for response in response_stream:
                print(response.choices[0].message)
                
            return "Not done", ["Not implemented yet."]
        
    def full_process(self, audio:io.BytesIO)->io.BytesIO:
        transcribed = self.audio_to_text(audio)  
        cohere_response = self.cohere_response(transcribed)
        audio_buffer = self.text_to_audio(cohere_response)
        
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
        
        

if __name__ == "__main__":
    # For a small voice input (4,5,6), this took 12-13 seconds. Can we cut this down? 
        # Update: this is now 9 seconds.
    agent = AudioAgent(debug=True)
    agent.full_process(open("./output.mp3", 'rb'))