import streamlit as st
import subprocess
import os
import threading
import time
import requests
from flask import Flask, request, jsonify, send_file
import openai
import tempfile
import io
import base64
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
flask_app = Flask(__name__)

# Set your OpenAI API key
openai.api_key = os.environ.get("OPENAI_API_KEY")
if not openai.api_key:
    logger.warning("OPENAI_API_KEY environment variable not set!")

# Flask routes
@flask_app.route('/text-to-speech', methods=['POST'])
def text_to_speech():
    """
    Endpoint for converting text to speech using OpenAI TTS model
    """
    try:
        # Get request data
        data = request.json
        
        if not data or 'text' not in data:
            logger.warning("Missing 'text' parameter in request")
            return jsonify({"error": "Missing 'text' parameter"}), 400
        
        text = data.get('text')
        voice = data.get('voice', 'alloy')  # Default voice is 'alloy'
        
        logger.info(f"Processing text-to-speech request with voice: {voice}")
        
        # Call OpenAI API for text-to-speech
        response = openai.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )
        
        # Get the raw audio content
        audio_data = response.content
        
        # Create a file-like object from the binary content
        audio_io = io.BytesIO(audio_data)
        audio_io.seek(0)
        
        logger.info(f"Successfully generated speech, returning audio file")
        
        # Send the audio file directly from memory
        return send_file(
            audio_io,
            mimetype='audio/mpeg',
            as_attachment=True,
            download_name='speech.mp3'
        )
    
    except Exception as e:
        logger.error(f"Error in text-to-speech: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@flask_app.route('/speech-to-text', methods=['POST'])
def speech_to_text():
    """
    Endpoint for converting speech to text using OpenAI Whisper model
    """
    try:
        audio_file = None
        temp_filename = None
        
        # Handle form upload
        if request.files and 'audio_file' in request.files:
            audio_file = request.files['audio_file']
            
            logger.info(f"Received audio file upload: {audio_file.filename}")
            
            # Create a temp file to save the audio
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{audio_file.filename.split(".")[-1]}') as temp_file:
                temp_filename = temp_file.name
                audio_file.save(temp_filename)
            
            # Properly open the file for OpenAI's API
            audio_file = open(temp_filename, 'rb')
        
        # Handle base64 encoded audio
        elif request.is_json and request.json and 'audio_base64' in request.json:
            base64_audio = request.json.get('audio_base64')
            file_type = request.json.get('file_type', 'mp3')
            
            logger.info(f"Received base64 encoded audio with file type: {file_type}")
            
            # Decode base64 string
            audio_data = base64.b64decode(base64_audio)
            
            # Create a temp file to save the audio
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_type}') as temp_file:
                temp_filename = temp_file.name
                temp_file.write(audio_data)
            
            # Properly open the file for OpenAI's API
            audio_file = open(temp_filename, 'rb')
        
        else:
            logger.warning("No audio file provided in request")
            return jsonify({"error": "No audio file provided. Send a form with 'audio_file' or JSON with 'audio_base64'"}), 400
        
        # Call OpenAI API for speech-to-text
        logger.info("Calling OpenAI Whisper API for transcription")
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
        
        # Close the file before responding
        audio_file.close()
        
        logger.info("Successfully transcribed audio")
        return jsonify({"text": transcript.text})
    
    except Exception as e:
        logger.error(f"Error in speech-to-text: {str(e)}", exc_info=True)
        return jsonify({"error": str(e), "type": str(type(e))}), 500
    
    finally:
        # Clean up resources
        if 'audio_file' in locals() and audio_file is not None:
            try:
                audio_file.close()
            except:
                pass
        
        if 'temp_filename' in locals() and temp_filename and os.path.exists(temp_filename):
            try:
                os.unlink(temp_filename)
            except:
                pass

@flask_app.route('/', methods=['GET'])
def home():
    """
    Home endpoint with basic instructions
    """
    logger.info("Home endpoint accessed")
    return jsonify({
        "app": "OpenAI Speech API",
        "status": "running",
        "endpoints": {
            "text-to-speech": {
                "url": "/text-to-speech",
                "method": "POST",
                "description": "Convert text to speech",
                "body": {
                    "text": "Text to convert to speech",
                    "voice": "alloy (optional)"
                }
            },
            "speech-to-text": {
                "url": "/speech-to-text",
                "method": "POST",
                "description": "Convert speech to text",
                "form-data": {
                    "audio_file": "Audio file to transcribe"
                },
                "or-json": {
                    "audio_base64": "Base64 encoded audio string",
                    "file_type": "mp3 (optional)"
                }
            }
        }
    })

# Function to run Flask in a separate process
def run_flask():
    from waitress import serve
    port = 8888
    logger.info(f"Starting Flask server on port {port}")
    serve(flask_app, host="0.0.0.0", port=port)

# Start Flask server in a separate thread
flask_thread = threading.Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()

# Wait for Flask to start up
time.sleep(2)

# Streamlit UI
st.set_page_config(
    page_title="Speech Conversion API",
    page_icon="🎤",
    layout="wide"
)

st.title("🎤 OpenAI Speech Conversion")

# Create tabs for the different services
tab1, tab2 = st.tabs(["Text to Speech", "Speech to Text"])

with tab1:
    st.header("Convert Text to Speech")
    
    # Text input for the text to convert
    text_input = st.text_area("Enter text to convert to speech:", height=150)
    
    # Voice selection
    voice_options = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
    selected_voice = st.selectbox("Select voice:", voice_options)
    
    # Convert button
    if st.button("Convert to Speech"):
        if not text_input:
            st.error("Please enter some text to convert.")
        else:
            with st.spinner("Converting text to speech..."):
                try:
                    # Call the Flask API endpoint
                    response = requests.post(
                        "http://localhost:8888/text-to-speech",
                        json={"text": text_input, "voice": selected_voice}
                    )
                    
                    if response.status_code == 200:
                        # Create audio player
                        st.success("Conversion successful!")
                        st.audio(response.content, format="audio/mp3")
                        
                        # Download button
                        st.download_button(
                            label="Download Audio",
                            data=response.content,
                            file_name="speech.mp3",
                            mime="audio/mp3"
                        )
                    else:
                        st.error(f"Error: {response.json().get('error', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Error connecting to API: {str(e)}")

with tab2:
    st.header("Convert Speech to Text")
    
    # File uploader for audio
    uploaded_file = st.file_uploader("Upload an audio file", type=["mp3", "wav", "m4a", "ogg"])
    
    # Record audio option (placeholder - would require additional JavaScript)
    st.write("Or record audio directly (coming soon)")
    
    # Convert button
    if st.button("Transcribe Audio"):
        if not uploaded_file:
            st.error("Please upload an audio file to transcribe.")
        else:
            with st.spinner("Transcribing audio..."):
                try:
                    # Call the Flask API endpoint
                    files = {"audio_file": (uploaded_file.name, uploaded_file, "audio/mpeg")}
                    response = requests.post("http://localhost:8888/speech-to-text", files=files)
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.success("Transcription successful!")
                        
                        # Display transcription
                        st.markdown("### Transcription")
                        st.write(result["text"])
                        
                        # Copy button
                        st.text_area("Transcription (copy)", value=result["text"], height=150)
                    else:
                        st.error(f"Error: {response.json().get('error', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Error connecting to API: {str(e)}")

# Display API status
st.sidebar.title("API Status")
try:
    response = requests.get("http://localhost:8888/")
    if response.status_code == 200:
        st.sidebar.success("API is running")
        st.sidebar.json(response.json())
    else:
        st.sidebar.error("API returned an error")
except Exception as e:
    st.sidebar.error(f"Cannot connect to API: {str(e)}")

# API Key configuration
st.sidebar.title("Configuration")
api_key = st.sidebar.text_input("OpenAI API Key", type="password")
if st.sidebar.button("Update API Key"):
    os.environ["OPENAI_API_KEY"] = api_key
    openai.api_key = api_key
    st.sidebar.success("API Key updated!")

# Footer
st.sidebar.markdown("---")
st.sidebar.info("This application uses OpenAI's API for text-to-speech and speech-to-text conversion.")