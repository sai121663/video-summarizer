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
import requests

import nest_asyncio
nest_asyncio.apply()


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
    url = request.args.get('url')
    
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    video_id = extract_video_id(url)
    
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL'}), 400
    
    try:
        response = requests.get(
            f'https://api.supadata.ai/v1/youtube/transcript',
            headers={'x-api-key': os.getenv('SUPADATA_API_KEY')},
            params={'videoId': video_id}
        )
        data = response.json()
        full_transcript = ' '.join([entry['text'] for entry in data['content']])
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
    
    Use proper markdown headings (##, ###) for all section titles. Do not use bold (**text**) for titles or subheadings.

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
    clean = re.sub(r'#{1,6}\s*(.*)', r'\1.', summary)  # add period after headers
    clean = re.sub(r'(\d)️⃣', r'\1.', clean)  # Replace keycap emojis but keep the number
    clean = re.sub(r'[*`_~]', '', clean)  # remove remaining markdown
    clean = re.sub(r'\|', ' ', clean)  # replace table pipes
    clean = re.sub(r'\n+', ' ', clean)  # replace newlines with spaces
    clean = re.sub(r'\s+', ' ', clean)  # collapse multiple spaces
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F9FF"
        u"\U00002700-\U000027BF"
        u"\U0001FA00-\U0001FA6F"
        u"\u0030-\u0039\u20E3"  # keycap numbers 0-9
        u"\u2600-\u26FF"        # miscellaneous symbols
        u"\u2700-\u27BF"        # dingbats
        "]+", flags=re.UNICODE)
    clean = emoji_pattern.sub('', clean)

    try:
        tmp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_audio.mp3')
        
        # Use edge-tts Python API directly instead of subprocess
        async def generate():

            # Debugging
            print(f"Temp path: {tmp_path}")
            print(f"Clean text length: {len(clean)}")

            communicate = edge_tts.Communicate(clean, voice="en-US-AndrewNeural")
            await communicate.save(tmp_path)

            print(f"File exists after save: {os.path.exists(tmp_path)}")
            print(f"File size after save: {os.path.getsize(tmp_path)}")


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