"""
    Front-end for app. Handles user audio input, 
    which runs whisper on the input and relays it (as text) back to the server.
    Server should then handle it and return Success or Failure.
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
import pyaudio
import numpy as np
import wave
import time
import io
import sounddevice as sd
from pydub import AudioSegment
import os

from audio_configs import CHUNK, CHANNELS, RATE, FORMAT

# Import backend for now. In the future, switch this over to a server and ping endpoints.
from back_end import BackEnd 

# To run the app, simply run the Python file.

class AudioLevelApp(App):
    def __init__(self, threshold=10, debug=False):
        self.recording=False
        self.start_time=0
        self.end_time=0
        self.debug=debug
        self.threshold=threshold
        self.backend=BackEnd()
        
        super(AudioLevelApp, self).__init__()
        
        self.intro_user()
        
    def intro_user(self):
        """
            Play user introduction audio.
        """
        
        if "intro.mp3" not in os.listdir("./"):
            intro_audio = self.backend.generate_intro()
            with open("intro.mp3", "wb") as f:
                f.write(intro_audio.getvalue())
        
        intro_audio = io.BytesIO()
        with open("intro.mp3", "rb") as f:
            intro_audio.write(f.read())
        intro_audio.seek(0)
                
        intro_audio = AudioSegment.from_mp3(intro_audio)
        sample_rate = intro_audio.frame_rate
        num_channels = intro_audio.channels
        sample_width = intro_audio.sample_width
                
        raw_data = np.array(intro_audio.get_array_of_samples())
        if sample_width == 2:
            dtype = np.int16
        elif sample_width == 4:
            dtype = np.int32
        else:
            dtype = np.int8
            
        audio_array = raw_data.astype(dtype)
        
        if num_channels > 1: # reshape array for multi channel audio
            audio_array = audio_array.reshape(-1, num_channels)
            
        sd.play(audio_array, samplerate=sample_rate)
    
    def build(self):
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        # Label to display audio level
        self.label = Label(text="Audio Level: 0.00", font_size='40sp')
        self.layout.add_widget(self.label)
        
        if self.debug:
            # Buttons to toggle recording
            self.record_button = Button(text='Start Recording', font_size='30sp')
            self.record_button.bind(on_press=self.toggle_recording)
            self.layout.add_widget(self.record_button)
        
        return self.layout
    
    def on_start(self):
        # Iniitalize PyAudio
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        Clock.schedule_interval(self.update_audio_level, 0.0001)
    
    def toggle_recording(self, instance=None):
        # Manually enable recording 
        
        # Toggle recording state
        self.recording = not self.recording
        
        if self.recording:
            # Start recording
            if instance: self.record_button.text = "Stop recording"
            self.start_recording()
        else:
            # Stop recording
            self.record_button.text = "Start Recording"
            self.stop_recording()
            
    def start_recording(self):
        # Initialize list to store audio frames
        self.frames = []
        
        # Record start time
        self.start_time = time.time()
        
        # Schedule update function to run periodically
        Clock.schedule_interval(self.update_audio_level, 0.0001)

    def stop_recording(self):
        # Record end time
        self.end_time = time.time()
        
        # Save recorded audio to a file
        self.save_audio()
        
        # Print recording duration
        print(f"Recording duration: {self.end_time - self.start_time:.2f} seconds")
    
    def update_audio_level(self, dt):
        data = self.stream.read(CHUNK, exception_on_overflow=False) # Read 1024 frames from current audio
        audio_data = np.frombuffer(data, dtype=np.int16)            
                
        # Calcualte RMS volume and update label with level
        rms = np.sqrt(np.mean(np.square(audio_data)))
        self.label.text = f"Audio Level: {rms:.2f}"

        print(rms)
        if rms > self.threshold:
            # Sometimes, this picks up background noise and defaults to "bye-bye".
            if not self.recording:
                self.recording = True
                self.start_recording()
        
        
        if self.recording:           
            # Read audio from microphone
            boosted_audio_data = audio_data * 20.0
            
            # Clip the values to prevent overflow (16-bit signed integers range from -32768 to 32767)
            boosted_audio_data = np.clip(boosted_audio_data, -32768, 32767)
            boosted_audio_data = boosted_audio_data.astype(np.int16)
            
            self.frames += [boosted_audio_data.tobytes()] # Save audio data for recording
            
            if rms <= self.threshold and ((time.time() - self.start_time) > 3):
                self.recording = False
                self.stop_recording()            
            
            print("Recording...", len(self.frames))
            
    
    def save_audio(self):
        # Save recorded audio to WAV file

        # File-like object in memory to pass to back-end class
        audio_file = io.BytesIO()

        # Below may be buggy - needs testing
        with wave.open(audio_file, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(self.audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b"".join(self.frames))
            
        # Pass to agent, get voice output
        response_audio = self.backend.full_process(audio_file)

        # Save to local memory for debug purposes
        if self.debug:        
            with open("output.mp3", "wb") as f:
                f.write(audio_file.getvalue())
            print("Recoding saved to output.wav")
        
            with open("agent_output.mp3", "wb") as f:
                response_audio.seek(0)
                f.write(response_audio.getvalue())
            print("Recoding saved to agent_output.wav")
            
        # Play audio back to user
        response_audio.seek(0)
        
        audio = AudioSegment.from_mp3(response_audio)
        
        sample_rate = audio.frame_rate
        num_channels = audio.channels
        sample_width = audio.sample_width
                
        raw_data = np.array(audio.get_array_of_samples())
        if sample_width == 2:
            dtype = np.int16
        elif sample_width == 4:
            dtype = np.int32
        else:
            dtype = np.int8
            
        audio_array = raw_data.astype(dtype)
        
        if num_channels > 1: # reshape array for multi channel audio
            audio_array = audio_array.reshape(-1, num_channels)
            
        # Play audio, and wait until it finishes
        sd.play(audio_array, samplerate=sample_rate)
        # sd.wait()

    def on_stop(self):
        # Clean up mic audio stream
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()
    
if __name__ == "__main__":    
    ma = AudioLevelApp(threshold=15, debug=True)
    ma.run()