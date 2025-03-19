from flask import Flask, request, jsonify, send_file
import openai
import os
import tempfile
import io
import base64
from pydub import AudioSegment

app = Flask(__name__)

# Set your OpenAI API key
# Replace with your actual OpenAI API key or set as environment variable

@app.route('/text-to-speech', methods=['POST'])
def text_to_speech():
    """
    Endpoint for converting text to speech using OpenAI TTS model
    
    Expected JSON format:
    {
        "text": "Text to convert to speech",
        "voice": "alloy" (optional, defaults to "alloy")
    }
    
    Returns:
    Audio file in mp3 format
    """
    try:
        # Get request data
        data = request.json
        
        if not data or 'text' not in data:
            return jsonify({"error": "Missing 'text' parameter"}), 400
        
        text = data.get('text')
        voice = data.get('voice', 'alloy')  # Default voice is 'alloy'
        
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
        
        # Send the audio file directly from memory
        return send_file(
            audio_io,
            mimetype='audio/mpeg',
            as_attachment=True,
            download_name='speech.mp3'
        )
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    finally:
        # Clean up the temp file
        if 'temp_filename' in locals():
            try:
                os.unlink(temp_filename)
            except:
                pass

@app.route('/speech-to-text', methods=['POST'])
def speech_to_text():
    """
    Endpoint for converting speech to text using OpenAI Whisper model
    
    Expected form-data:
    - audio_file: The audio file to transcribe
    OR
    Expected JSON format (if using base64):
    {
        "audio_base64": "base64 encoded audio string",
        "file_type": "mp3" (optional, defaults to "mp3")
    }
    
    Returns:
    JSON with transcribed text
    """
    response_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
    try:
        audio_file = None
        temp_filename = None
        
        # Handle form upload
        if request.files and 'audio_file' in request.files:
            audio_file = request.files['audio_file']
            
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
            
            # Decode base64 string
            audio_data = base64.b64decode(base64_audio)
            
            # Create a temp file to save the audio
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_type}') as temp_file:
                temp_filename = temp_file.name
                temp_file.write(audio_data)
            
            # Properly open the file for OpenAI's API
            audio_file = open(temp_filename, 'rb')
        
        else:
            return jsonify({"error": "No audio file provided. Send a form with 'audio_file' or JSON with 'audio_base64'"}), 400
        
        # Call OpenAI API for speech-to-text
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
        
        # Close the file before responding
        audio_file.close()

        response = jsonify({"text": transcript.text})
        for key, value in response_headers.items():
            response.headers[key] = value
        return response
        
        # return jsonify({"text": transcript.text})
    
    except Exception as e:
        # Add more detailed error information
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

@app.route('/', methods=['GET'])
def home():
    """
    Home endpoint with basic instructions
    """
    return jsonify({
        "app": "OpenAI Speech API",
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
