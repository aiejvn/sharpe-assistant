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
incoming_queue = Queue() # server -> client

# Test server response by sending generic audio
try:
    with open("user_input.mp3", "rb") as f:
        input_audio = io.BytesIO(f.read())
        input_audio.seek(0)
        arr, _ = sf.read(input_audio, dtype='float32')
        arr = arr.astype(np.float32)
        # Flatten if stereo
        if arr.ndim > 1:
            arr = arr.reshape(-1, 1).flatten()

        for start in range(0, len(arr), CHUNK):
            chunk = arr[start:start + CHUNK]
            outgoing_queue.put(chunk)
except Exception as e:
    print(f"Could not preload user_input.mp3: {e}")

async def audio_stream_client(uri):
    async with websockets.connect(uri) as ws:
        print("Connected to Websocket server.")
        
        # Receives audio from microphone
        # input_stream = sd.InputStream(
        #     samplerate=RATE,
        #     channels=CHANNELS,
        #     dtype=DTYPE,
        #     blocksize=CHUNK,
        #     callback=audio_callback
        # )

        # Plays audio to output devices
        output_stream = sd.OutputStream(
            samplerate=RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=CHUNK,
            callback=output_callback
        )
        
        # with input_stream, output_stream:
        with output_stream:
            print("Audio streams started. Press CTRL-C to stop.")
            
            while True:
                # Receive audio from server
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=0.1)
                    data = json.loads(message)
                    if data["type"] == "audio":
                        incoming_queue.put(data["data"])
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
    if status: print(f"Output status: {status}")
        
    if incoming_queue.empty():
        outdata.fill(0)
    else:
        audio_chunk = incoming_queue.get()
        
        n = min(len(audio_chunk), CHUNK)
        outdata[:n, 0] = audio_chunk[:n] # (frames x channels) shape, channels=1
        if n < len(outdata): # If audio is shorter than CHUNK (4096 atm)
            outdata[n:, 0] = 0
    
        

async def main():
    server_uri = "ws://localhost:5000/ws"
    try:
        await audio_stream_client(server_uri)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Client disconnected")
        
        
if __name__ == "__main__":
    asyncio.run(main())