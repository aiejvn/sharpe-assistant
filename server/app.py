import openai 
from openai import OpenAI
from dotenv import load_dotenv

# Audio
import io
import os

# MCP
from tools.cohere_tool import CohereTool
from tools.perplexity_tool import PerplexityTool
# from tools.calendar_tool import CalendarTool

import string

from flask import Flask, request, jsonify

# From root of project, run:
# docker run --env-file ./server/.env --name test-ls kyjvn/flaskapp 
# to spin up an image.

# To stop:
# docker stop test-ls && docker rm test-ls

app = Flask(__name__)

class BackEnd:
    
    def __init__(self, streaming=False, debug=False):
        self.streaming = streaming
        self.debug = debug

        load_dotenv()
        
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        self.perplexity = PerplexityTool(streaming=self.streaming)        
        self.cohere = CohereTool(streaming=self.streaming)
        # self.calendar = CalendarTool()        
        
        self.convo = [
            {
                "role": "system",
                "content": (
                    "You are Sharpe, an artificial intelligence assistant, and you need to "
                    "engage in a helpful, detailed, polite conversation with a user. "
                    # f"This user lives at {address}. Incorporate this into your search IF AND ONLY IF "
                    f"This user lives near Queen's University, Kingston, Ontario. Incorporate this into your search IF AND ONLY IF the user asks for anything related to location."
                    "Keep responses as brief as possible. Finish your responses by asking if the user if they need help with anything else."
                ),
            },
        ]
        
    def audio_to_text(self, audio_file:io.BytesIO)->str:
        audio_file.seek(0) # Reset file pointer to beginning
        print(f"Size of audio file input: {audio_file.getbuffer().nbytes} bytes")
        
        # IoBytes is not accepted by whisper - .mp3 is
        temp_filepath = "user_input.mp3"
        with open(temp_filepath, "wb") as f:
            audio_file.seek(0) # Reset file pointer to beginning
            f.write(audio_file.getvalue())
            
        print("Wrote to user_input.mp3.")
        
        transcription = openai.audio.transcriptions.create(
            model="whisper-1", 
            file=open(temp_filepath, "rb"),
        )
        
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
    
    
    def use_tool(self, text:str):
        """
            Given user voice input, determine what they want
            in constant time, and return a fitting result in tuple(tool:str, res:str) form.
            Note: this is not natural language input, but rather command input
            parsed algorithmically.
        """        
        translator = str.maketrans('', '', string.punctuation)
        terms = text.split()
        if len(terms) < 2:
            return ('cohere', self.cohere.cohere_response(self.convo)) # Handle input smaller than two words.
        
        print(terms[0].lower().translate(translator))
        print(terms[1].lower().translate(translator))
        print(terms[2:])
        try:
            match terms[0].lower().translate(translator):
                case "search":
                    # User wants to search for something
                    # Google it and return it
                    return ('perplexity_search', self.perplexity.perplexity_response(self.convo)[0])
                
                case "desktop":
                    # Indicate client must parse result
                    return ('client_side_required', text)
                
                case _:
                    print("Using cohere.")
                    # If they don't want any tools, they prob want reasoning
                    return ('cohere', self.cohere.cohere_response(self.convo))
                
                # case "calendar":                    
                #     match terms[1].lower().translate(translator):
                #         case "view":
                #             # Find the conditions on which user wants to view events
                #             # return them
                            
                            
                #             # "calendar view 10 April 25 May 10"
                #                 # event number (if exists)
                #                 # start date
                #                 # end date
                            
                #             # -> FOUND USER SAID: Calendar, view 10, Monday 12, Tuesday 14.
                #                 # Months kinda buggy rn
                #             print("Now viewing calendar events...")
                                
                #             event_number = int(terms[2].translate(translator))
                #             start_date = f"{terms[3]} {terms[4]}".translate(translator)
                #             end_date = f"{terms[5]} {terms[6]}".translate(translator)

                #             event_list = self.calendar.read_events(start_date=start_date, end_date=end_date, num_events=event_number)
                #             if event_list: 
                #                 n = len(event_list)
                #                 event_str = ""
                #                 for i in range(n):
                #                     event_str += f"Event {i}: {event_list[i][0]} \n"
                #                 print("Found events:", event_str)
                #                 return ('calendar', event_str)
                #             else:
                #                 return ('calendar', "No events found.")
                            
                #         case "add":
                #             # Find where user wants to add event
                #             # return success or failure
                            
                #             # "calendar add April 18 6:30 April 18 6:45 My Event"
                #             NotImplementedError()
                            
                #         case "edit":
                #             # Find what event user wants to edit, edit it
                #             # return success or failure
                #             NotImplementedError()

                #         case "delete":
                #             # Find what event user wants to delete, delete it
                #             # return success or failure
                #             NotImplementedError()
                
                #         case _:
                #             # Ok what do u want user...
                #             return ('Tool Not Found', f"Could not find tool: {terms[1]} for {terms[0]}" )
        except Exception as e:
            return ('Error', str(e))
        
    
        
    def full_process(self, audio:io.BytesIO)->io.BytesIO:
        transcribed = self.audio_to_text(audio)  
        print("FOUND USER SAID:", transcribed)

        self.convo += [{
            "role": "user",
            "content": (transcribed),
        }]

        tool_used, text_response = self.use_tool(transcribed)
        print("Used tool:", tool_used)
        print("Responding with", text_response)
        
        if tool_used != 'client_side_required':    
            audio_buffer = self.text_to_audio(text_response)
            
            self.convo += [{
                "role": "system",
                "content": (text_response),
            }]
            
            return audio_buffer
        else:
            print("Client side required...")
            return text_response
    
    def generate_voice(self, text:str="Hi! I'm Sharpe, your personal hands-free assistant. How may I help you today?"):
        """
            Call TTS.
        """
        response = openai.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="coral",
            input=text
        )
            
        audio_buffer = io.BytesIO(response.content) # Write straight to buffer
        audio_buffer.seek(0)
      
        return audio_buffer
        
    
# ----- APP STUFF -----
backend = BackEnd()

@app.route('/call_assistant', methods=['POST'])
def call_assistant_endpoint():
    """
        Allows users to call the app for Sharpe responses.
        Expects an audio file in the request.
    """
    if 'audio' not in request.files:
        return jsonify({"error":"No audio file provided."}, 400)
    
    audio_file = request.files['audio']
    audio_buffer = io.BytesIO(audio_file.read())
    print(f"Size of audio_buffer: {audio_buffer.getbuffer().nbytes} bytes")
    
    try:
        response = backend.full_process(audio_buffer)
        if type(response) != str:
            return response.getvalue(), 200, {'Content-Type': 'audio/mpeg'}
        else:
            return jsonify({"response": response}), 200
        
    except Exception as e:
        print("Got error:", str(e))
        return jsonify({"error": str(e)}), 500
    
@app.route('/voice', methods=['POST'])
def make_voice():
    if 'text' not in request.json:
        return jsonify({"error": "No text provided in the request."}), 400

    user_text = request.json['text']
    print(f"User passed text: {user_text}")
    
    audio = backend.generate_voice(user_text)
    print(f"Size of audio_buffer: {audio.getbuffer().nbytes} bytes")

    return audio.getvalue(), 200, {'Content-Type': 'audio/mpeg'}
        
if __name__ == "__main__":
    # For a small voice input (4,5,6), this took 12-13 seconds. Can we cut this down? 
        # Update: this is now 9 seconds.
    load_dotenv()
    if os.getenv("FLASK_ENV") == "production":    
        app.run(debug=False, port=5000)
    else:
        app.run(debug=True, port=5000)