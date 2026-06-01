# Imports
from flask import Flask, request, jsonify 
from flask_cors import CORS
from youtube_transcript_api import YouTubeTranscriptApi
import re 
import anthropic
from dotenv import load_dotenv
import os
import edge_tts, asyncio, io
import tempfile
import subprocess

load_dotenv()

# Creating the Flask server
app = Flask(__name__)
CORS(app)

# Extract the video's ID using regex
    # In the link, the ID usually comes after "?v=..."
def extract_video_id(url): 
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(pattern, url)
    return match.group(1) if match else None

# ENDPOINT #1: Generate Transcript
    # Calls extract_video_id() to get the transcript
    # Gets the transcript using YouTubeTranscriptApi library
    # Joins all the transcript chunks into a large string
    # Returns the string as JSON
@app.route('/transcript', methods=['GET'])
def get_transcript():

    # Get the URL that was entered through the request 
    url = request.args.get('url')

    # Error handling for an empty URL
    if not url: 
        return jsonify({'error': 'No URL provided'}), 400

    # Get the video ID for the URL
    video_id = extract_video_id(url)

    # Error handling for an invalid video ID
    if not video_id: 
        return jsonify({'error': 'Invalid YouTube URL'}), 400

    # Fetch and return the video's transcript 
    try: 
        transcript_data = YouTubeTranscriptApi().fetch(video_id)
        full_transcript = ' '.join([entry.text for entry in transcript_data])
        # return jsonify({'transcript': full_transcript})
        return jsonify({
            'transcript': full_transcript,
            'thumbnail': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'
        })

    except Exception as e: 
        return jsonify({'error': str(e)}), 500

# ENDPOINT #2: Summarize transcript
@app.route('/summarize', methods=['POST'])
def summarize():

    # Receiving data 
        # If no level is specified, it defaults to "beginner"
    data = request.get_json()
    transcript = data.get('transcript')
    level = data.get('level', 'beginner')

    # Setting up the API key
    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    # Instruction prompt that will be fed to Claude
    prompt = f"""Summarize this video for a {level} audience.
    
    - Beginner: Assume no background knowledge & explain in simple terms. Include analogies & emojis to keep it engaging. Focus on the "what" and "why"
    - Intermediate: Assume some background knowledge. Cover key concepts & their significance. Avoid over-explaining basics. 
    - Expert: Expert-level knowledge assumed. Use precise technical terminology, highlight nuanced insights & methods. 
    Here is the transcript: {transcript}"""

    try: 
        # Sending the message to Claude & waiting for a response
        message = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        # Returning Claude's response as a JSON for React to display
        return jsonify({'summary': message.content[0].text})

    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({'error': str(e)}), 500

# ENDPOINT #3: Convert summary to audio
@app.route('/speak', methods=['POST', 'OPTIONS'])
def speak():
    if request.method == 'OPTIONS':
        return '', 200

    data = request.get_json()
    summary = data.get('summary', '')

    # Cleaning the text
    clean = re.sub(r'[#*`]', '', summary)
    clean = re.sub(r'\n+', ' ', clean)
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F9FF"
        u"\U00002700-\U000027BF"
        u"\U0001FA00-\U0001FA6F"
        "]+", flags=re.UNICODE)
    clean = emoji_pattern.sub('', clean)

    try:
        tmp_path = r"C:\Users\saith\OneDrive\Documents\CS Summer Projects\YouTube-Video-Summarizer\temp_audio.mp3"

        # Use edge-tts Python API directly instead of subprocess
        async def generate():
            communicate = edge_tts.Communicate(clean, voice="en-US-AndrewNeural")
            await communicate.save(tmp_path)

        asyncio.run(generate())

        print(f"File size: {os.path.getsize(tmp_path)}")

        with open(tmp_path, 'rb') as f:
            audio_data = f.read()

        print(f"Audio size: {len(audio_data)}")
        return app.response_class(audio_data, mimetype="audio/mpeg")

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500




if __name__ == '__main__':
    app.run(debug=True)