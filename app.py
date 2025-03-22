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

from audio_configs import CHUNK, CHANNELS, RATE, FORMAT

# To run the app, simply run the Python file.

class AudioLevelApp(App):
    def __init__(self, debug=False):
        self.recording=False
        self.start_time=0
        self.end_time=0
        self.debug=debug
        super(AudioLevelApp, self).__init__()
    
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
        if rms > 1:
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
            
            if rms <= 1 and ((time.time() - self.start_time) > 3):
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

        # Save to local memory for debug purposes
        if self.debug:        
            with wave.open("output.wav", "wb") as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(self.audio.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b"".join(self.frames))
            print("Recoding saved to output.wav")
        
    def on_stop(self):
        # Clean up mic audio stream
        self.stream.stop_stream()
        self.steam.close()
        self.audio.terminate()
    
if __name__ == "__main__":    
    ma = AudioLevelApp(debug=True)
    ma.run()