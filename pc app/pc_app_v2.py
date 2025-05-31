"""
    New front-end for app. 
    Implements bi-directional websocket audio streaming.
"""

import asyncio
import websockets
import io
import sounddevice as sd
import numpy as np
import json
from queue import Queue
from audio_configs import *

# Queues for audio data
outgoing_queue = Queue() # client -> server
incoming_queue = Queue() # server -> client

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
            print("Audio streams started. Press CTRL-C to stop.")
            
            while True:
                # Send audio to server
                if not outgoing_queue.empty():
                    audio_chunk = outgoing_queue.get() # float32 -> value between -1 and 1 representing amplitude
                    await ws.send(json.dumps({
                        "type":"audio",
                        "data": audio_chunk.tolist()
                    }))
                    print(audio_chunk.tolist()) # We're sending stuff...
                    
                # Receive audio from server
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=0.1)
                    data = json.loads(message)
                    if data["type"] == "audio":
                        incoming_queue.put(np.array(data["data"], dtype=np.float32))
                except asyncio.TimeoutError:
                    pass
                except Exception as e:
                    print(f"Error receiving data: {e}")
                    break
                    
        
def audio_callback(indata, frames, time, status):
    '''
        Callback function for audio input
    '''
    if status: print(f"Input status: {status}")
    outgoing_queue.put(indata.copy())
    # print(f'Called audio callback function! Outgoing queue is now {outgoing_queue.qsize()} items.')


def output_callback(outdata, frames, time, status):
    '''
        Callback function for audio input
    '''
    if status: print(f"Output status: {status}")
        
    if incoming_queue.empty():
        outdata.fill(0)
    else:
        audio_chunk = incoming_queue.get()
        outdata[:] = audio_chunk.reshape(-1, 1) # (frames x channels) shape, channels=1
    # print(f'Called output callback function! Incoming queue is now {incoming_queue.qsize()} items.')
    
        

async def main():
    server_uri = "ws://localhost:5000/ws"
    try:
        await audio_stream_client(server_uri)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Client disconnected")
        
        
if __name__ == "__main__":
    # print(sd.query_devices())
    # print(sd.default.device)
    asyncio.run(main())
    
    # 5-30-2025 update: im sending my audio back to myself rn?