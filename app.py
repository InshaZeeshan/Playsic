from flask import Flask, render_template, redirect, request
import requests
import json
app = Flask(__name__)

# Replace these values with your Spotify app details
CLIENT_ID = '071e87f9bc66436889c57d3af513e1fb'
CLIENT_SECRET = 'ee4db2057c354787a94c0408a9aa9525'
REDIRECT_URI = 'http://127.0.0.1:5000/callback'
SPOTIFY_AUTHORIZE_URL = 'https://accounts.spotify.com/authorize'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'

# This variable will store the user's access token
user_access_token = None

# Function to create a playlist on the user's Spotify account
def create_playlist(playlist_name, access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    url = 'https://api.spotify.com/v1/me/playlists'
    data = {'name': playlist_name}
    response = requests.post(url, headers=headers, json=data)
    return response.json() if response.status_code == 201 else None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/team")
def team():
    return render_template("team.html")

@app.route("/input")
def input():
    return render_template("input.html")

@app.route("/thankyou")
def thankyou():
    return render_template("thankyou.html")


@app.route("/authorize_spotify")
def authorize_spotify():
    return redirect(
        f"{SPOTIFY_AUTHORIZE_URL}"
        f"?client_id={CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=playlist-modify-private%20playlist-modify-public"
    )

@app.route("/callback")
def callback():
    global user_access_token

    # Get the authorization code from the Spotify callback
    code = request.args.get('code')

    # Exchange the authorization code for access and refresh tokens
    response = requests.post(
        SPOTIFY_TOKEN_URL,
        data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
        }
    )

    # Handle the response, extract the access token, and store it
    if response.status_code == 200:
        data = response.json()
        user_access_token = data['access_token']

        # Redirect the user to the "input" page after obtaining the access token
        return redirect("/input")
    else:
        response.raise_for_status()
        print(f"Error during authorization: {response.text}")
        return f"Error during authorization: {response.text}"





@app.route("/create_playlist", methods=['POST'])
def handle_playlist_creation():
    global user_access_token

    if user_access_token is not None:
        playlist_name = request.form.get('playlistName')
        playlist_genre = request.form.getlist('playlistGenre')  # Get selected genres
        playlist_languages = request.form.getlist('playlistLanguages')  # Get selected languages
        num_tracks = int(request.form.get('numTracks'))  # Get number of tracks from the form
        release_year_start = request.form.get('releaseYearStart')  # Get start year from the form
        release_year_end = request.form.get('releaseYearEnd')  # Get end year from the form

        # Create the playlist
        response = create_playlist(playlist_name, user_access_token)

        if response:
            playlist_id = response['id']  # Retrieve the playlist ID from the response

            # Construct search queries for each combination of genre, language, and release year
            tracks_to_add = []
            for genre in playlist_genre:
                for language in playlist_languages:
                    # Use Spotify API to search for tracks based on genre, language, and release year
                    search_query = f"genre:{genre} artist:{language} year:{release_year_start}-{release_year_end}"
                    print(f"Search Query: {search_query}")  # Print the search query

                    search_response = requests.get(
                        f"https://api.spotify.com/v1/search?q={search_query}&type=track&limit={num_tracks}",
                        headers={'Authorization': f'Bearer {user_access_token}'}
                    )
                    if search_response.status_code == 200:
                        tracks_data = search_response.json().get('tracks', {}).get('items', [])
                        print(f"Tracks Found: {len(tracks_data)}")  # Print the number of tracks found
                        tracks_to_add.extend([track['uri'] for track in tracks_data])

            # Trim the number of tracks to match the specified limit
            if len(tracks_to_add) > num_tracks:
                tracks_to_add = tracks_to_add[:num_tracks]

            # Add discovered tracks to the playlist
            if tracks_to_add:
                add_tracks_url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
                add_tracks_response = requests.post(
                    add_tracks_url,
                    headers={'Authorization': f'Bearer {user_access_token}', 'Content-Type': 'application/json'},
                    data=json.dumps({'uris': tracks_to_add})
                )

                if add_tracks_response.status_code == 201:
                    return f"Playlist '{playlist_name}' created and tracks added successfully!"
                else:
                    return "Playlist created, but failed to add tracks."
            else:
                return "No tracks found based on selected criteria."
        else:
            return "Failed to create the playlist."
    else:
        return "Access token not found."





if __name__ == "_main_":
    app.run(debug=True)