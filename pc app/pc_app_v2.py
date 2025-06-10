"""
    New front-end for app. 
    Implements bi-directional websocket audio streaming.
"""

import asyncio
import websockets
import io
import sounddevice as sd
import soundfile as sf
import numpy as np
import json
from queue import Queue
from audio_configs import *

# TODO: Limit the rate at which we play audio output (chipmunk bug)z

# Queues for audio data
outgoing_queue = Queue() # client -> server

# server -> client
incoming_buffer = bytearray() 

# Test server response by sending generic audio
# try:
#     with open("user_input.mp3", "rb") as f:
#         input_audio = io.BytesIO(f.read())
#         input_audio.seek(0)
#         arr, _ = sf.read(input_audio, dtype='float32')
#         arr = arr.astype(np.float32)
#         # Flatten if stereo
#         if arr.ndim > 1:
#             arr = arr.reshape(-1, 1).flatten()

#         for start in range(0, len(arr), CHUNK):
#             chunk = arr[start:start + CHUNK]
#             outgoing_queue.put(chunk)
# except Exception as e:
#     print(f"Could not preload user_input.mp3: {e}")
    
    
def print_queue_sizes():
    outgoing_queue_bytes = 0
    for item in list(outgoing_queue.queue):
        if isinstance(item, bytes):
            outgoing_queue_bytes += len(item)
        elif isinstance(item, np.ndarray):
            outgoing_queue_bytes += item.nbytes
        else:
            outgoing_queue_bytes += len(bytes(item))
    print(f"Total bytes in outgoing_queue: {outgoing_queue_bytes}")

    # Print total number of bytes in client2server_queue
    print(f"Total bytes in incoming_queue: {len(incoming_buffer)}")

async def audio_stream_client(uri):
    async with websockets.connect(uri) as ws:
        print("Connected to Websocket server.")
        
        # Receives audio from microphone
        input_stream = sd.InputStream(
            samplerate=RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=CHUNK,
            callback=audio_callback
        )

        # Plays audio to output devices
        output_stream = sd.OutputStream(
            samplerate=RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=CHUNK,
            callback=output_callback
        )
        
        with input_stream, output_stream:
        # with output_stream:
            print("Audio streams started. Press CTRL-C to stop.")
            
            while True:
                # Receive audio from server
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=0.1)
                    data = json.loads(message)
                    if data["type"] == "audio":
                        global incoming_buffer
                        
                        arr = np.array(data["data"], dtype=np.float32)
                        arr = np.clip(arr, -1.0, 1.0)
                        arr_pcm16 = (arr * 32767).astype(np.int16)
                        incoming_buffer += arr_pcm16.tobytes()
                        print(f"Received {len(data['data'])} elements of audio.")
                    else:
                        print("No audio received from back-end.")                    
                except asyncio.TimeoutError:
                    pass
                except Exception as e:
                    print(f"Error receiving data: {e}")
                    break
                    
                # Send audio to server
                if not outgoing_queue.empty():
                    audio_chunk = outgoing_queue.get() # float32 -> value between -1 and 1 representing amplitude
                    audio_chunk = np.array(audio_chunk) * 5 # Amplify
                    
                    await ws.send(json.dumps({
                        "type":"audio",
                        "data": audio_chunk.tolist()
                    }))
                    print(f'Sent {len(audio_chunk.tolist())} elements of audio.')
                
                try:
                    print_queue_sizes()
                except Exception as e:
                    print(f"Error printing queue sizes: {e}")
        
def audio_callback(indata, frames, time, status):
    '''
        Callback function for audio input
    '''
    if status: print(f"Input status: {status}")
    outgoing_queue.put(indata.copy())


def output_callback(outdata, frames, time, status):
    '''
        Callback function for playing audio
    '''
    global incoming_buffer
    if status: print(f"Output status: {status}")
    slow_factor = 2 # Input will play at 0.5x speed 
        
    bytes_needed = max(frames * 2 // slow_factor, 1)
    if len(incoming_buffer) >= bytes_needed:
        chunk = incoming_buffer[:bytes_needed]
        incoming_buffer = incoming_buffer[bytes_needed:]
    else:
        chunk = incoming_buffer + b'\x00' * (bytes_needed - len(incoming_buffer))
        incoming_buffer = bytearray()
    
    # Convert bytes to int16 numpy array, then to float32 in [-1, 1]
    audio_np = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
    audio_np = np.repeat(audio_np, slow_factor)
    
    # Insert into outdata (handle mono)
    outdata[:, 0] = audio_np[:frames] if len(audio_np) >= frames else np.pad(audio_np, (0, frames - len(audio_np)))

async def main():
    server_uri = "ws://localhost:5000/ws"
    try:
        await audio_stream_client(server_uri)
    except Exception as e:
        print(f"Main loop error: {e}")
    finally:
        print("Client disconnected")
        
        
if __name__ == "__main__":
    asyncio.run(main())