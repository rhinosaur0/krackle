import socketio
import secrets
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import base64
import numpy as np
from io import BytesIO
from PIL import Image
import time

# from test import get_eigenFace_mse
from emotionTest import predict_emotion

# Load environment variables from .env file


# Initialize FastAPI and Socket.IO
app = FastAPI()
sio = socketio.AsyncServer(async_mode='asgi', 
                           cors_allowed_origins='*')

# Mount the Socket.IO server to FastAPI
app.mount("/socket.io", socketio.ASGIApp(sio))

# CORS Configuration
origins = [
    'https://krackle.co',
    'https://www.krackle.co',
    'https://test.krackle.co',
    'http://localhost:3000'
]

app.add_middleware(
    CORSMiddleware,
    allow_origins='*',
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# In-memory storage for lobbies
lobbies = {}

# Root route for checking the server
@app.get("/")
async def root():
    return {"message": "Socket.IO Backend is running."}

# Socket.IO Event Handling
@sio.event
async def connect(sid, environ):
    print(f"A user connected: {sid}")

@sio.event
async def createGame(sid, gameData):
    print(f'Create Game Event Received: {gameData}')
    
    # Generate a unique game ID
    gameId = secrets.token_hex(4)
    
    # Create a new lobby
    lobbies[gameId] = {
        'admin': sid,
        'settings': {
            'adminName': gameData['adminName'],
            'timer': gameData['timer'],
            'rounds': gameData['rounds'],
            'maxPlayers': gameData['players']
        },
        'players': [],
        'round_start_time': None
    }
    lobby = lobbies[gameId]
    player = {'id': sid, 'name': gameData['adminName'], 'emotion_history': [(0, (None, []))]}
    lobby['players'].append(player)
    # Admin joins the lobby room
    await sio.enter_room(sid, gameId)

    # Emit 'createGameResponse' back to the admin client
    await sio.emit('createGameResponse', {'success': True, 'gameId': gameId}, to=sid)

    await sio.emit('playerJoined', player, room=gameId)

    # Emit successful join to the player
    await sio.emit('joinLobbyResponse', {'success': True, 'lobbyCode': gameId}, to=sid)

@sio.event
async def joinLobby(sid, data):
    lobbyCode = data['lobbyCode']
    playerName = data['playerName']
    print(f"Join Lobby Event Received: LobbyCode={lobbyCode}, PlayerName={playerName}")
    
    lobby = lobbies.get(lobbyCode)
    if lobby:
        if len(lobby['players']) < lobby['settings']['maxPlayers']:
            if not lobby['round_start_time']:
                player = {'id': sid, 'name': playerName, 'emotion_history': [(0, (None, []))]}
                lobby['players'].append(player)

                players_names = [player['name'] for player in lobby['players']]
                await sio.enter_room(sid, lobbyCode)

                # Emit 'playerJoined' to the lobby room
                await sio.emit('playerJoined', player, room=lobbyCode, to=lobbyCode)

                # Emit successful join to the player
                await sio.emit('joinLobbyResponse', {'success': True, 'lobbyCode': lobbyCode, 'playerList': players_names}, to=sid)
            else:
                await sio.emit('joinLobbyResponse', {'success': False, 'message': 'Game already started, please wait until the game is finished.'}, to=sid)

        else:
            # Lobby full
            await sio.emit('joinLobbyResponse', {'success': False, 'message': 'Lobby is full.'}, to=sid)
        
    
    else:
        # Lobby not found
        await sio.emit('joinLobbyResponse', {'success': False, 'message': 'Lobby not found.'}, to=sid)

@sio.event
async def startGame(sid, lobbyCode):

    lobby = lobbies.get(lobbyCode)
    if lobby and lobby['admin'] == sid:
        # Emit 'gameStarted' to all players in the lobby
        lobby['round_start_time'] = time.time()
        players_names = [player['name'] for player in lobby['players']]
        await sio.emit('gameStarted', {'gameSettings': lobby['settings'], 'room': lobbyCode, 'players': players_names}, to=lobbyCode)
    else:
        # Unauthorized or lobby not found
        await sio.emit('startGameResponse', {'success': False, 'message': 'Unauthorized or lobby not found.'}, to=sid)

@sio.event
async def disconnect(sid):
    print(f"User disconnected: {sid}")

    # Remove player from any lobbies they were part of
    for gameId, lobby in lobbies.items():
        playerIndex = next((i for i, p in enumerate(lobby['players']) if p['id'] == sid), None)
        if playerIndex is not None:
            removedPlayer = lobby['players'].pop(playerIndex)
            await sio.emit('playerLeft', removedPlayer, room=gameId)

        # If the disconnected user was the admin, handle lobby closure
        if lobby['admin'] == sid:
            del lobbies[gameId]
            await sio.emit('lobbyClosed', {'message': 'Lobby has been closed by the admin.'}, room=gameId)


# WebSocket route to handle webcam data and send back processing results
@sio.event
async def webcam_data(sid, data):
    # Process the webcam data (base64 image)

    lobby_code = data['lobbyCode']
    lobby = lobbies.get(lobby_code)

    base64_data = data['image'].split(",")[1]
    # Decode the base64 image
    image_data = base64.b64decode(base64_data)
    player_number = 0
    for i, player in enumerate(lobby['players']):
        if player['id'] == sid:
            player_number = i
    message = None

    try:
        print(lobby['players'][player_number]['emotion_history'])
        image = Image.open(BytesIO(image_data))
        # Convert to OpenCV format
        image_np = np.array(image)
        # lobby['players'][player_number]['emotion_history'] = [
        #         entry for entry in lobby['players'][player_number]['emotion_history']
        #         if (time.time() - lobby['round_start_time'] - entry[0]) <= 6
        # ]

        # history = lobby['players'][player_number]['emotion_history']
        # result= get_eigenFace_mse(image_np, history)
        
        # if result != None:
        #     history_append, game_over = (time.time() - lobby['round_start_time'], result[0]), result[1]
        #     print('face detected')
        #     if game_over == True:
        #         message = 'roundLost'
        # else:
        #     history_append = (time.time() - lobby['round_start_time'], (None, []))
        #     print('still no face detected')     
        # lobby['players'][player_number]['emotion_history'].append(history_append)
        preds = predict_emotion(image_np)
        print(preds)
        
    except:
        print('no image detected')

    await sio.emit('webcam_response', {'message': message}, to=sid)


# Run the FastAPI app
# if __name__ == "__main__":
# uvicorn.run(app, host="127.0.0.1", port=8000)  # Running on port 8001, as port 8000 is taken by npm start
