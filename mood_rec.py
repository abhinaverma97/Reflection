import webbrowser

emotion_to_content = {
    "happy": {
        "song": "https://open.spotify.com/playlist/37i9dQZF1DXdPec7aLTmlC",  # Happy Hits
        "movie": "https://www.netflix.com/browse/genre/6548",  # Comedies
        "activity": "Call a friend or go outside for a walk!"
    },
    "sad": {
        "song": "https://open.spotify.com/playlist/37i9dQZF1DX3rxVfibe1L0",  # Sad Songs
        "movie": "https://www.netflix.com/browse/genre/6384",  # Dramas
        "activity": "Try journaling or listening to a calming podcast."
    },
    "angry": {
        "song": "https://open.spotify.com/playlist/37i9dQZF1DWUvHZA1zLcjW",  # Calm Vibes
        "movie": "https://www.netflix.com/browse/genre/10683",  # Meditation/Soothing
        "activity": "Try a short breathing exercise or meditation."
    },
    "surprise": {
        "song": "https://open.spotify.com/playlist/37i9dQZF1DX3LyU0mhqC2v",  # Dance Hits
        "movie": "https://www.netflix.com/browse/genre/43040",  # Action & Adventure
        "activity": "Explore a new hobby or trivia game online."
    },
    "neutral": {
        "song": "https://open.spotify.com/playlist/37i9dQZF1DX4sWSpwq3LiO",  # Lo-Fi Chill
        "movie": "https://www.netflix.com/browse/genre/34399",  # Feel-good movies
        "activity": "Take a break, do some stretches or grab a tea."
    },
    "fear": {
        "song": "https://open.spotify.com/playlist/37i9dQZF1DWZqd5JICZI0u",  # Deep Focus
        "movie": "https://www.netflix.com/browse/genre/81427741",  # Motivational
        "activity": "Practice grounding techniques or yoga."
    },
    "disgust": {
        "song": "https://open.spotify.com/playlist/37i9dQZF1DX3YSRoSdA634",  # Chillhop
        "movie": "https://www.netflix.com/browse/genre/10375",  # Stand-up comedy
        "activity": "Vent in a journal or clean up your space."
    }
}

def suggest_based_on_emotion(emotion):
    suggestion = emotion_to_content.get(emotion.lower())
    if not suggestion:
        print("No suggestion for this emotion.")
        return

    print(f"\n🎵 Playing music: {suggestion['song']}")
    print(f"🎬 Movie genre suggestion: {suggestion['movie']}")
    print(f"🧘 Activity: {suggestion['activity']}")
    
    webbrowser.open(suggestion['song'])  # Auto-play song in browser
    # Optionally open movie or activity links as well
    # webbrowser.open(suggestion['movie'])

# Example usage
# suggest_based_on_emotion("happy")
