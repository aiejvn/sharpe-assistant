import io
import openai

def audio_to_text(audio_file:io.BytesIO)->str:
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


def text_to_audio(text:str)->io.BytesIO:
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
    
    with open("voice_output.mp3", "wb") as f:
        f.write(audio_buffer.getvalue())

    return audio_buffer

def generate_voice(text:str="Hi! I'm Sharpe, your personal hands-free assistant. How may I help you today?"):
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