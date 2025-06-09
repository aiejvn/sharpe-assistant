# HTML APIs
from openai import OpenAI
from dotenv import load_dotenv

# Audio
import io
import os
import soundfile as sf

# Realtime API
from audio_configs import *
import base64
import json
import pyaudio
import socks
import socket
import threading
import time
import websocket

socket.socket = socks.socksocket
WS_URL = 'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01'

# MCP
from tools.cohere_tool import CohereTool
from tools.perplexity_tool import PerplexityTool

# Server Websocket Modules 
from flask import Flask
from flask_sock import Sock
import numpy as np
from queue import Queue
import sounddevice as sd

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
        
        # Queues for audio data between client and server, to be served via websockets
        self.client2server_queue = Queue()
        self.server2client_queue = Queue()
        
        # Audio output stream
            # Is this still useful?
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
                                    
        # Test sending audio to client by filling output queue
        # try:
        #     with open("user_input.mp3", "rb") as f:
        #         input_audio = io.BytesIO(f.read())
        #         input_audio.seek(0)
        #         arr, _ = sf.read(input_audio, dtype='float32')
        #         arr = arr.astype(np.float32)
        #         # Flatten if stereo
        #         if arr.ndim > 1:
        #             arr = arr.reshape(-1, 1).flatten()
                
        #         samples_per_chunk = 1024 
        #         # print(samples_per_chunk) # should be 1024
        #         for start in range(0, len(arr), samples_per_chunk):
        #             chunk = arr[start:start + samples_per_chunk]
        #             self.server2client_queue.put(chunk)
        # except Exception as e:
        #     print(f"Could not preload user_input.mp3: {e}")
    
        
    # ===== REALTIME API STARTS HERE ===== 
    
    # TODO: Fix audio being too amplified bug
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
                        self.server2client_queue.put(audio_content)
                        print(f'OpenAI: audio content is of type {type(audio_content)}.')
                        print(f'OpenAI: Received {len(audio_content)} bytes.')
                    
                    case 'input_audio_buffer.speech_started':
                        print("OpenAI: New speech started, clearing buffer and stopping playback.")
                        self.stop_audio_playback()
                        
                    case 'response.audio.done':
                        print('OpenAI: AI is finished speaking.')
                    
                    case 'response.function_call_arguments.done':
                        self.handle_function_call(message, ws)
                        
                    case 'error':
                        print('OpenAI: Error occurred when sending package. Should investigate further.')
                        print(message)
                
                
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
            
            return ws
            
        except Exception as e:
            print(f'Failed to connect to OpenAI: {e}')
            
            
    # ===== REALTIME API ENDS HERE =====
    
    def send_backend_audio_to_client(self, ws):
        while True:
            if not self.server2client_queue.empty():
                audio_chunk = self.server2client_queue.get() # 'bytes'
                
                if isinstance(audio_chunk, bytes):
                    # Assume 16-bit PCM, little-endian
                    audio_chunk = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) 
                    # print("1", audio_chunk)
                    audio_chunk = audio_chunk / 32768.0
                elif isinstance(audio_chunk, np.ndarray):
                    audio_chunk = audio_chunk.astype(np.float32)
                else:
                    audio_chunk = np.array(audio_chunk, dtype=np.float32)
                    
                # print("2", audio_chunk)
                    
                try:
                    ws.send(json.dumps({
                        'type':'audio',
                        # 'data':list(audio_chunk)
                        'data':audio_chunk.tolist()
                    }))
                    print('Sent data to client.')     
                except Exception as e:
                    print(f'Error in sending audio to client: {e}')
                time.sleep(0.005)
            else: 
                print('Server to client queue is empty.') 
            time.sleep(0.05) # wait 50 ms to check again
        
    def print_queue_sizes(self):
        server2client_total_bytes = 0
        for item in list(self.server2client_queue.queue):
            if isinstance(item, bytes):
                server2client_total_bytes += len(item)
            elif isinstance(item, np.ndarray):
                server2client_total_bytes += item.nbytes
            else:
                server2client_total_bytes += len(bytes(item))
        print(f"Total bytes in server2client_queue: {server2client_total_bytes}")

        # Print total number of bytes in client2server_queue
        client2server_total_bytes = 0
        for item in list(self.client2server_queue.queue):
            if isinstance(item, bytes):
                client2server_total_bytes += len(item)
            elif isinstance(item, np.ndarray):
                client2server_total_bytes += item.nbytes
            else:
                client2server_total_bytes += len(bytes(item))
        print(f"Total bytes in client2server_queue: {client2server_total_bytes}")
    
    
# ========== APP STUFF ==========
backend = BackEnd()


@sock.route('/ws')
def websocket_handler(ws):
    print('Websocket client connected.')
    
    client_thread = threading.Thread(target=backend.send_backend_audio_to_client, args=(ws,))
    client_thread.start()
    
    # Read output_audio_test.bin and fill the server2client_queue
    # try:
    #     with open("output_audio_test.bin", "rb") as f:
    #         while True:
    #             chunk = f.read(CHUNK)
    #             if not chunk:
    #                 break
    #             backend.server2client_queue.put(chunk)
    #     print("Loaded output_audio_test.bin into server2client_queue.")
    # except Exception as e:
    #     print(f"Could not load output_audio_test.bin: {e}")
    
    try:
        while True:
            data = ws.receive()
            if data is None:
                print('Websocket client disconnected.')
                backend.output_stream.stop()
                break
            
            # Note: if no output is returned, output may need to be louder.
                            
            try:
                data = json.loads(data)    
                # backend.test_realtime_api_with_mp3()

            except Exception as e:
                print(f'Invalid JSON from client: {e}')
                continue
            
            if data.get('type') == 'audio':
                backend.print_queue_sizes()
                    
                backend.client2server_queue.put(np.array(data['data'], dtype=np.float32))
                
                if not backend.client2server_queue.empty():
                    audio_data = backend.client2server_queue.get() # numpy.ndarray
                    # note: sometimes, the app may get stuck reading a queue. this results in nothing being executed
                    audio_as_file = io.BytesIO()
                    sf.write(audio_as_file, data=audio_data, samplerate=24000, format='RAW', subtype='PCM_16')
                
                    audio_as_file.seek(0) # Reset file pointer to beginning
                    print(f"Size of audio file input: {audio_as_file.getbuffer().nbytes} bytes")
                    
                    try:
                        while True:
                            chunk = audio_as_file.read(CHUNK)
                            if not chunk:
                                break
                            
                            encoded_chunk = base64.b64encode(chunk).decode('utf-8')
                            message = json.dumps({
                                'type': 'input_audio_buffer.append',
                                'audio': encoded_chunk
                            })
                            backend.openai_ws.send(message)
                            print(f'Sent {len(chunk)} bytes of audio data to OpenAI realtime API.')
                            
                            time.sleep(0.10) # To avoid being rate limited
                    except Exception as e:
                        print(f'OpenAI: Exception in sending audio to realtime API: {e}')
                else:
                    print('Client to server queue is empty.')              
        
                
    except Exception as e:
        print(f'Websocket error: {e}')
        backend.output_stream.stop()
    finally:
        print('Websocket handler exited.')
        
if __name__ == "__main__":
    app.run(port=5000)
    # app.run(port=5000, debug=True)