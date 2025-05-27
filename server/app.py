# API's
import openai 
from openai import OpenAI
from dotenv import load_dotenv

# Audio
import io
import os

# Realtime API
import json
import socks
import socket
import websocket
import threading
import base64
import time
import pyaudio
from audio_configs import *

socket.socket = socks.socksocket
WS_URL = 'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01'

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
        
        self.audio_buffer = bytearray()
        
        # Initialization of Realtime API stuff
        self.ws = self.connect_to_openai(api_key=os.getenv('OPENAI_API_KEY'))
        
        p = pyaudio.PyAudio()
        
        speaker_stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=24000,
            output=True,
            stream_callback=self.speaker_callback,
            frames_per_buffer=CHUNK
        )
        
        self.audio_buffer = bytearray() 

        p = pyaudio.PyAudio()
        
        # Audio playing stuff, move to front-end 
        # self.speaker_stream = p.open(
        #     format=FORMAT,
        #     channels=CHANNELS,
        #     rate=24000,
        #     output=True,
        #     stream_callback=self.speaker_callback,
        #     frames_per_buffer=CHUNK
        # )
        # self.speaker_stream.start_stream()

        self.speaker_stream = None

        # Testing Realtime API stuff
        self.test_realtime_api_with_mp3()
    
        
        
    # ===== REALTIME API STARTS HERE ===== 
    
    def receive_audio_from_websocket(self, ws):
        self.audio_buffer
        
        try:
            while True: # No stop condition since we're on a server
                message = ws.recv()
                if not message: # empty message (EOF or connection closed)
                    print('Received empty message (possible EOF or WebSocket closing')
                
                message = json.loads(message)
                event_type = message['type']
                print(f'Received WebSocket Event: {event_type}')
                
                match event_type:
                    case 'session.created':
                        self.send_session_update(ws)
                    
                    case 'response.audio.delta':
                        audio_content = base64.b64decode(message['delta'])
                        self.audio_buffer.extend(audio_content)
                        print(f'Received {len(audio_content)} bytes. Total audio buffer size: {len(self.audio_buffer)}')
                    
                    case 'input_audio_buffer.speech_started':
                        print("New speech started, clearing buffer and stopping playback.")
                        self.clear_audio_buffer()
                        self.stop_audio_playback()
                        
                    case 'response.audio.done':
                        print('AI is finished speaking.')
                    
                    case 'response.function_call_arguments.done':
                        self.handle_function_call(message, ws)
                
                
        except Exception as e:
            print(f"Error receiving audio: {e}")
        finally:
            print('Exiting receive_audio_from_websocket thread.')
            
    
    def handle_function_call(self, event_json, ws):
        """
            Tool-calling goes here.
            OpenAI decides it on their end.
        """
        
        # Example json input: 
        # name=search 
        # call_id=call_319SRx808YpFiXuC 
        # arguments={"query":"new laptops 2025"} 
        # function_arguments={'query': 'new laptops 2025'}
        try:
            # 2nd arg is default value (if value is not found)
            name = event_json.get('name', "")
            call_id = event_json.get("call_id", "")

            arguments = event_json.get("arguments", "{}")
            function_call_args = json.loads(arguments)
            
            print("Found following for function call:", name, call_id, arguments, function_call_args)
            
            # Add search->perplexity here
            match name:
                
                case "get_updated_knowledge":
                    # perplexity here
                    try:
                        print("Using Perplexity Tool.")
                        # text, citations = self.perplexity.perplexity_response(arguments["query"])
                    
                    except Exception as e:
                        print(f"Error using Perplexity Tool on input: {e}")
                
                case "browser_search":
                    # send to client via websocket
                    try:
                        print(f"Using browser_search tool on input.")
                        # ...
                    except Exception as e:
                        print(f"Error using browser_search tool on input: {e}")
            
        except Exception as e:
            print(f"Error parsing function call arguments: {e}")
    
            
            
    def clear_audio_buffer(self):
        self.audio_buffer
        self.audio_buffer = bytearray()
        print('Audio buffer cleared.')
    
    
    def stop_audio_playback(self):
        return 

        stop_client_playing(client_ws)

                        
    def send_session_update(self, ws):
        from session_config import realtime_api_config 
        
        # Declare initial prompt, tools, etc. 
        session_config = realtime_api_config
        
        # Convert session config to JSON string
        print("Attempting to send session update.")
        session_config_json = json.dumps(session_config)
        
        try:
            ws.send(session_config_json)
        except Exception as e:
            print(f"Failed to send session update: {e}")
                        
        
    def send_audio_to_websocket(self, ws, audio:io.BytesIO):
        audio.seek(0) # Reset file pointer to beginning
        print(f"Size of audio file input: {audio.getbuffer().nbytes} bytes")
        CHUNK_SIZE = 4096
        
        try:
            while True:
                chunk = audio.read(CHUNK_SIZE)
                if not chunk:
                    break
                
                encoded_chunk = base64.b64encode(chunk).decode('utf-8')
                message = json.dumps({
                    'type': 'input_audio_buffer.append',
                    'audio': encoded_chunk
                })
                ws.send(message)
                print(f'Sent {len(chunk)} bytes of audio data to OpenAI realtime API.')
        except Exception as e:
            print(f'Exception in send_audio_to_websocket thread: {e}')
        finally:
            print('Exiting send_audio_to_websocket thread')
            
            
    def create_connection_with_ipv4(self, *args, **kwargs):
        """
            Creates a websocket connection using IPv4.
        """
        # Enforce use of IPv4
        original_getaddrinfo = socket.getaddrinfo
        
        # socket.AF_INET forces IPv4 protocol 
        def getaddrinfo_ipv4(host, port, family=socket.AF_INET, *args):
            return original_getaddrinfo(host, port, socket.AF_INET, *args) 
        
        # Monkey-patch function for IPv4 connection, then replace it iwth the original when done
        socket.getaddrinfo = getaddrinfo_ipv4
        try:
            return websocket.create_connection(*args, **kwargs)
        finally:
            socket.getaddrinfo = original_getaddrinfo
        
        
    def connect_to_openai(self, api_key):
        """
            Start up a websocket connection to OpenAI's realtime API.
        """
        ws = None
        try:
            ws = self.create_connection_with_ipv4(
                WS_URL,
                header = [
                    f'Authorization: Bearer {api_key}',
                    'OpenAI-Beta: realtime=v1'
                ]
            )
            print('Connected to OpenAI Websocket.')
            
            # Start the recv and send threads
            # These will run independently of the function, terminating when their target functions terminate
            receive_thread = threading.Thread(target=self.receive_audio_from_websocket, args=(ws,))
            receive_thread.start()
            
            """
                When we receive audio from the client, send it to the websocket.
                We do not need to make another thread for this.
            """
            # mic_thread = threading.Thread(target=self.send_audio_to_websocket, args=(ws,audio_buffer,))
            # mic_thread.start()
            return ws
            
        except Exception as e:
            print(f'Failed to connect to OpenAI: {e}')
            
    def speaker_callback(self, in_data, frame_count, time_info, status):
        """
            Function to handle received audio playback.
            Runs on a thread to automatically play audio data when called.
        """
        bytes_needed = frame_count * 2
        current_buffer_size = len(self.audio_buffer)
        
        if current_buffer_size >= bytes_needed:
            # Take the first n bytes off the bytearray
            audio_chunk = bytes(self.audio_buffer[:bytes_needed])
            self.audio_buffer = self.audio_buffer[bytes_needed:]
        else:
            # Pad the rest of the data with empty bytes
            audio_chunk = bytes(self.audio_buffer) + b'\x00' * (bytes_needed - current_buffer_size)
            self.audio_buffer.clear()
            
        return (audio_chunk, pyaudio.paContinue) 
    
    
    def create_output_audio_thread(self):
        """
            Plays self.audio_buffer on a separate thread when called.
        """
        recv_thread = threading.Thread(target=self.receive_audio_from_websocket, args=(self.ws,))
        recv_thread.start()
        
        return recv_thread
        
    
    def full_process(self, audio:io.BytesIO):
        """
            General function to call for processing a user's request.
            
            - audio: the io.BytesIO representation of the input.
            
            Note: The audio data type may change once we set up websockets
            between the front-end and the server.l    
        """
        audio.seek(0)        
        
        # Main command flow
        recv_thread = self.create_output_audio_thread()
        
        self.send_audio_to_websocket(self.ws, audio)

        # Wait for receiver to finish
        recv_thread.join(timeout=30)
    
            
    def test_realtime_api_with_mp3(self):
        """
            Function to test if realtime API works.
            Saving to output seems to have some issues. 
        """
        
        with open("user_input.mp3", "rb") as f:
            input_audio = io.BytesIO(f.read())
        
        self.full_process(input_audio)

            
    # ===== REALTIME API ENDS HERE =====
        
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
                
        except Exception as e:
            return ('Error', str(e))
        
    
        
    # def full_process(self, audio:io.BytesIO)->io.BytesIO:
    #     transcribed = self.audio_to_text(audio)  
    #     print("FOUND USER SAID:", transcribed)

    #     self.convo += [{
    #         "role": "user",
    #         "content": (transcribed),
    #     }]

    #     tool_used, text_response = self.use_tool(transcribed)
    #     print("Used tool:", tool_used)
    #     print("Responding with", text_response)
        
    #     if tool_used != 'client_side_required':    
    #         audio_buffer = self.text_to_audio(text_response)
            
    #         self.convo += [{
    #             "role": "system",
    #             "content": (text_response),
    #         }]
            
    #         return audio_buffer
    #     else:
    #         print("Client side required...")
    #         return text_response
    
    def generate_voice(self, text:str="Hi! I'm Sharpe, your personal hands-free assistant. How may I help you today?"):
        """
            Call TTS.
        """
        response = openai.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
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
    # if os.getenv("FLASK_ENV") == "production":    
    #     app.run(debug=False, port=5000)
    # else:
    #     app.run(debug=True, port=5000)
        
    app.run(debug=False, port=5000)