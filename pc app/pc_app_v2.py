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
import time

# Queues for audio data
outgoing_queue = Queue() # client -> server

# server -> client
incoming_buffer = bytearray() 

is_recording = False
start_time = None

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
    print(f"Total bytes in incoming_buffer: {len(incoming_buffer)}")

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
                start = time.time()
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
                print(f"Main loop took {time.time() - start} seconds to run.")
        
def audio_callback(indata, frames, input_time, status):
    '''
        Callback function for audio input
    '''
    
    # BUG: Audio is choppy. Realtime API says we have mic errors. Make the recording smoother.
    global is_recording, start_time
    s = time.time()
    
    if status: print(f"Input status: {status}")
    multiplier = 1
    
    mean_level = np.abs(indata).mean()
    print(f"Mean audio level: {mean_level}")
    threshold = 0.01  
    if mean_level >= threshold:
        is_recording = True
        start_time = time.time()
    elif start_time and time.time() - start_time > 1:
        is_recording = False
        start_time = None
    
    if is_recording:  
        in_data = indata.copy() * multiplier # Make input audio audible to realtime api
        print(in_data)
        outgoing_queue.put(in_data)
    print(f"Audio callback took {time.time() - s} seconds to run.")


def output_callback(outdata, frames, output_time, status):
    '''
        Callback function for playing audio
    '''
    global incoming_buffer
    if status: print(f"Output status: {status}")

    s = time.time()
    slow_factor = 2 # Audio slows as this number increases
        
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
    print(f"Output callback took {time.time() - s} seconds to run.")

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