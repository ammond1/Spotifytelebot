import telebot
import telebot.formatting
from telebot.util import quick_markup
import spotipy
import os
import re
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

#loads env file
load_dotenv()
#gets all needed credentials
BOT_TOKEN = os.getenv('BOTTOKEN')
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')
bot = telebot.TeleBot(BOT_TOKEN)
scope = "playlist-modify-public, playlist-modify-private, user-read-playback-state"
sp_oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                        client_secret=SPOTIPY_CLIENT_SECRET,
                        redirect_uri=SPOTIPY_REDIRECT_URI,
                        scope=scope,
                        cache_path=".spotify_token_cache")

def get_spotify_client():
    token_info = sp_oauth.get_cached_token()
    if not token_info:
        auth_url = sp_oauth.get_authorize_url()
        print(f"Please navigate to the following URL to authorize: {auth_url}")
        # You need to handle the authorization outside the bot (e.g., in a web server).
        # For now, ask user to authorize manually and get the code.
        code = input("Enter the code from the URL: ")
        token_info = sp_oauth.get_access_token(code)
    return spotipy.Spotify(auth=token_info['access_token'])
sp = get_spotify_client()


def add_in(chatid):
    global to_add
    #get track uri
    track_id_match = re.search(r'/track/(\w+)', to_add[0])
    if track_id_match:
        track_id = track_id_match.group(1)
        # Construct track URI
        track_uri = f'spotify:track:{track_id}' 
    else:
        print("Invalid track URL")
        song_request(chatid)
        return None
    
    playlist_url = os.getenv('PLAYLISTURL')
    playlist_id_match = re.search(r'/playlist/(\w+)', playlist_url)
    if playlist_id_match:
        playlist_id = playlist_id_match.group(1)
    else:
        print("Invalid playlist URL")
        song_request(chatid)
        return None
    playlist_tracks= sp.playlist_items(playlist_id = playlist_url, fields= 'items.track.uri')['items']
    #checks if song is already in the playlist
    for i in playlist_tracks:
        playlist_tracks_uri = i['track']['uri']
        if playlist_tracks_uri == track_uri:
            bot.send_message(chat_id= chatid, text= "Song has already been previously added.")
            song_request(chatid)
            return None
    
    try:
        sp.playlist_add_items(playlist_id,[track_uri], position = None )
        keyboard_markup = quick_markup({
            'Add another' : {'callback_data' : 'add_music'},
            'Main menu' : {'callback_data' : 'back'}
        })
        bot.send_message(chat_id=chatid, text= 'Added successfully', reply_markup= keyboard_markup)
    except:
         keyboard_markup = quick_markup({
            'Try again' : {'callback_data' : 'add_music'},
            'Main menu' : {'callback_data' : 'back'}
        })
         bot.send_message(chat_id=chatid, text= 'Unsuccessful please try again', reply_markup= keyboard_markup)

    
def song_request(chatid):
    global to_add
    global state
    to_add = []
    keyboard_markup = quick_markup({
        'Back' : {'callback_data': 'back'}
    })
    bot.send_message(chat_id=chatid, text= "Please input song choice:", reply_markup= keyboard_markup)
    state = not state
    
#takes inputted text and searches it 
@bot.message_handler(func=lambda message: True and state == True)
def song_search(message):
    global state
    chatid= message.chat.id
    try:
        bot.send_message(chat_id=chatid, text='Searching...')
        # Search for the song
        results = sp.search(q=message.text, limit=1)
        # Check if there are any search results
        if results['tracks']['items']:
            keyboard_markup = quick_markup({
                'Add music' : {'callback_data' : 'add_in'},
                'Search again' : {'callback_data' : 'add_music'},
                'Main menu' : {'callback_data' : 'back'}
            }, row_width= 2)
            # Extract the track URL from the search results
            track_url = results['tracks']['items'][0]['external_urls']['spotify']
            to_add.append(track_url)
            hidden_link =telebot.formatting.hide_link(track_url)
            bold_text = telebot.formatting.hbold('If not the right song, click search again and input song name and artist name')
            bot.send_message(chat_id=chatid, 
                             text= f'{bold_text}{hidden_link}', 
                             reply_markup= keyboard_markup,
                             parse_mode= 'HTML'
                            )
        else:
            bot.send_message(chat_id=chatid, text="No matching tracks found. Try inputting song name and artist name.")
            song_search(message.chatid)

    except Exception as e:
        keyboard_markup = quick_markup({
            'Back' : {'callback_data' : 'add_music'}
        })
        bot.send_message(chat_id=chatid, text="An error occurred during the search.", reply_markup= keyboard_markup)
        print(f"Error: {e}")
    state = not state

#gives description of the app
def helps(chatid):
    bot_description = 'This bot helps add music of your choice into my spotify roadtrip playlist.'
    keyboard_markup = quick_markup({
        'Add Music' : {'callback_data' : 'add_music'},
        'Back' : {'callback_data' : 'back'}
    }, row_width= 2)
    bot.send_message(chat_id=chatid, text=bot_description, reply_markup= keyboard_markup)

#returns playlist link
def get_playlist(chatid):
    keyboard_markup = quick_markup({
        'Back' : {'callback_data' : 'back'},
    })
    bot.send_message(chat_id= chatid, text= os.getenv('PLAYLISTURL'), reply_markup= keyboard_markup)

#accesses what is currently playing
def currently_playing(chatid):
    current_playback= sp.currently_playing()
    if current_playback is not None and current_playback['is_playing']:
        track_url = current_playback['item']['external_urls']['spotify']
        track_name = current_playback['item']['name']
        track_artist= current_playback['item']['artists'][0]['name']
        keyboard_markup = quick_markup({
            'Back' : {'callback_data' : 'back'},
        })
        bot.send_message(chat_id= chatid, text= f'{track_name} by {track_artist} is currently playing\n{track_url}', reply_markup= keyboard_markup)
    else:
        keyboard_markup = quick_markup({
            'Back' : {'callback_data' : 'back'},
        })
        bot.send_message(chat_id= chatid, text= 'Nothing is playing right now check back again later', reply_markup= keyboard_markup)

#handles start command
@bot.message_handler(commands=['start'])
def start(message):
    global state
    state = False
    keyboard_markup = quick_markup({
        'Add Music': {'callback_data' : 'add_music'},
        'View Playlist' : {'callback_data' : 'get_playlist'},
        'Currently Playing' : {'callback_data' : 'currently_playing'},
        'About': {'callback_data':'help'}
    }, row_width=2)
    if type(message) == int:
        chatid = message
    else:
        chatid = message.chat.id
    bot.send_message(chat_id= chatid, text="What would you like to do", reply_markup= keyboard_markup)

#handles callback data
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    callback_data = call.data
    if callback_data in callback_functions:
        callback_functions[callback_data](call.message.chat.id)

#global variables
callback_functions = {
    "add_music" : song_request,
    "help" : helps,
    "back" : start,
    "add_in" : add_in,
    "get_playlist" : get_playlist,
    "currently_playing" : currently_playing,
}
to_add=[]
state = False
bot.infinity_polling()