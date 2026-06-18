# Imports
from flask import Flask, request, jsonify 
from flask_cors import CORS
from youtube_transcript_api import YouTubeTranscriptApi
import re 
import anthropic
from dotenv import load_dotenv
import os
import io
import subprocess
import requests


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

        # Error handling
        if response.status_code == 429: 
            return jsonify({'error': 'Transcript service limit reached. Please try again later.'}), 429
        elif response.status_code == 401: 
            return jsonify({'error': 'Transcript service authentication failed.'}), 401

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

    except anthropic.RateLimitError: 
        return jsonify({'error': 'AI service limit reached. Please try again later.'}), 429
    except anthropic.AuthenticationError: 
        return jsonify({'error': 'AI service authentication failed.'}), 401
    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)