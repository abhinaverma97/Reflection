import requests
import os

# API credentials
USER_ID = "i9FnxaKL1BhfJrBFB8pvQjEXipa2"  # Replace with your actual User ID
API_KEY = "ak-50dec0c9c9dc4c81b465be5bc35cf4d1"  # Replace with your actual API Key

# API endpoint
url = "https://api.play.ht/api/v2/tts/stream"

# Headers
headers = {
    "X-USER-ID": USER_ID,
    "AUTHORIZATION": API_KEY,
    "accept": "audio/mpeg",
    "content-type": "application/json"
}

# Request body
payload = {
    "text": "Hello from a realistic voice.",
    "voice_engine": "PlayDialog",
    "voice": "s3://voice-cloning-zero-shot/d9ff78ba-d016-47f6-b0ef-dd630f59414e/female-cs/manifest.json",
    "output_format": "mp3"
}

# Make the request and save the response to a file
response = requests.post(url, json=payload, headers=headers)

# Check if the request was successful
if response.status_code == 200:
    # Save the audio file
    with open("result.mp3", "wb") as f:
        f.write(response.content)
    print("Audio file saved as result.mp3")
else:
    print(f"Error: {response.status_code}")
    print(response.text)