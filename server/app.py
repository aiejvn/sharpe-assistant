# HTML APIs
import openai 
from openai import OpenAI
from dotenv import load_dotenv

# Audio
import io
import os
import soundfile as sf

# Realtime API
import json
import socks
import socket
import websocket
import threading
import base64
import pyaudio
from audio_configs import *

socket.socket = socks.socksocket
WS_URL = 'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01'

# MCP
from tools.cohere_tool import CohereTool
from tools.perplexity_tool import PerplexityTool

# Server Websocket Modules 
from flask import Flask
from flask_sock import Sock
import numpy as np
import sounddevice as sd
from queue import Queue

# From root of project, run:
# docker run --env-file ./server/.env --name test-ls kyjvn/flaskapp 
# to spin up an image.

# To stop:
# docker stop test-ls && docker rm test-ls

app = Flask(__name__)
sock = Sock(app)


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
        
        # Queues for audio data between client and server, to be served via websockets
        self.client2server_queue = Queue()
        self.server2client_queue = Queue()
        
        # Audio output stream
        self.output_stream = sd.OutputStream(
            samplerate=RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=CHUNK
        )
        self.output_stream.start()
        
        # Initialization of Realtime API stuff
        self.openai_ws = self.connect_to_openai(api_key=os.getenv('OPENAI_API_KEY'))
        
        p = pyaudio.PyAudio()
        # speaker_stream = p.open(
        #     format=FORMAT,
        #     channels=CHANNELS,
        #     rate=24000,
        #     output=True,
        #     stream_callback=self.speaker_callback,
        #     frames_per_buffer=CHUNK
        # )
        
        self.audio_buffer = bytearray() 
        
        # Test sending audio to client by filling output queue
        try:
            with open("user_input.mp3", "rb") as f:
                input_audio = io.BytesIO(f.read())
                input_audio.seek(0)
                arr, _ = sf.read(input_audio, dtype='float32')
                arr = arr.astype(np.float32)
                # Flatten if stereo
                if arr.ndim > 1:
                    arr = arr.reshape(-1, 1).flatten()
                
                samples_per_chunk = 1024 
                # print(samples_per_chunk) # should be 1024
                for start in range(0, len(arr), samples_per_chunk):
                    chunk = arr[start:start + samples_per_chunk]
                    self.server2client_queue.put(chunk)
        except Exception as e:
            print(f"Could not preload user_input.mp3: {e}")
    
        
    # ===== REALTIME API STARTS HERE ===== 
    
    def receive_audio_from_websocket(self, ws):
        try:
            while True: # No stop condition since we're on a server
                message = ws.recv()
                if not message: # empty message (EOF or connection closed)
                    print('OpenAI: Received empty message (possible EOF or WebSocket closing')
                
                message = json.loads(message)
                event_type = message['type']
                print(f'OpenAI: Received WebSocket Event: {event_type}')
                
                match event_type:
                    case 'session.created':
                        self.send_session_update(ws)
                    
                    case 'response.audio.delta':
                        audio_content = base64.b64decode(message['delta'])
                        self.audio_buffer.extend(audio_content)
                        self.server2client_queue.put(audio_content)
                        print(f'OpenAI: audio content is of type {type(audio_content)}.')
                        print(f'OpenAI: Received {len(audio_content)} bytes. Total audio buffer size: {len(self.audio_buffer)}')
                    
                    case 'input_audio_buffer.speech_started':
                        print("OpenAI: New speech started, clearing buffer and stopping playback.")
                        self.clear_audio_buffer()
                        self.stop_audio_playback()
                        
                    case 'response.audio.done':
                        print('OpenAI: AI is finished speaking.')
                    
                    case 'response.function_call_arguments.done':
                        self.handle_function_call(message, ws)
                
                
        except Exception as e:
            print(f"OpenAI: Error receiving audio: {e}")
        finally:
            print('OpenAI: Exiting receive_audio_from_websocket thread.')
            
    
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
            
            print("OpenAI: Found following for function call:", name, call_id, arguments, function_call_args)
            
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
        print("OpenAI: Attempting to send session update.")
        session_config_json = json.dumps(session_config)
        
        try:
            ws.send(session_config_json)
        except Exception as e:
            print(f"Failed to send session update: {e}")
                        
        
    def send_audio_to_websocket(self, ws):
        if not self.client2server_queue.empty():
            audio_data = self.client2server_queue.get() # numpy.ndarray
            audio_as_file = io.BytesIO()
            sf.write(audio_as_file, data=audio_data, samplerate=RATE, format='mp3')
        
            audio_as_file.seek(0) # Reset file pointer to beginning
            print(f"Size of audio file input: {audio_as_file.getbuffer().nbytes} bytes")
            CHUNK_SIZE = 4096
            
            try:
                while True:
                    chunk = audio_as_file.read(CHUNK_SIZE)
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
            between the front-end and the server.    
        """     
        
        # Main command flow
        recv_thread = self.create_output_audio_thread()
        
        # send_audio_to_realtime_api_thread = threading.Thread(target=self.send_audio_to_websocket, args=(ws,audio,))
        # send_audio_to_realtime_api_thread.start()

        # Wait for receiver to finish
        recv_thread.join(timeout=30)
    
            
    def test_realtime_api_with_mp3(self):
        """
            Function to test if realtime API works.
        """
        
        with open("user_input.mp3", "rb") as f:
            input_audio = io.BytesIO(f.read())
            input_audio.seek(0)
            arr, _ = sf.read(input_audio)
            self.client2server_queue.put(arr)
        
        self.full_process(input_audio)

            
    # ===== REALTIME API ENDS HERE =====
    
    
# ========== APP STUFF ==========
backend = BackEnd()


@sock.route('/ws')
def websocket_handler(ws):
    print('Websocket client connected.')
    
    # Start BG thread for managing realtime API calls + sending audio to client
    # threading.Thread(target=backend.audio_processing_worker, daemon=True).start()
    
    
    try:
        while True:
            data = ws.receive()
            if data is None:
                print('Websocket client disconnected.')
                backend.output_stream.stop()
                break
            
            try:
                data = json.loads(data)    
                
                threading.Thread(target=backend.send_audio_to_websocket, args=(backend.openai_ws)).start()
                # backend.test_realtime_api_with_mp3()

            except Exception as e:
                print(f'Invalid JSON from client: {e}')
                continue
            
            if data.get('type') == 'audio':
                backend.client2server_queue.put(np.array(data['data'], dtype=np.float32))
                
                if not backend.server2client_queue.empty():
                    audio_chunk = backend.server2client_queue.get()
                    # print(type(audio_chunk), audio_chunk)
                    if type(audio_chunk) == 'np.ndarray':
                        audio_chunk = audio_chunk.ravel() # convert to np.array
                        
                    # Amplify & send audio
                    audio_chunk = np.array(audio_chunk) * 5 
                    ws.send(json.dumps({
                        'type':'audio',
                        'data':audio_chunk.tolist()
                    }))
                    print('Sent data to client.')
                
    except Exception as e:
        print(f'Websocket error: {e}')
        backend.output_stream.stop()
    finally:
        print('Websocket handler exited.')
        
if __name__ == "__main__":
    app.run(port=5000)
    # app.run(port=5000, debug=True)