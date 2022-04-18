from cmath import phase
import functools
import json
from multiprocessing import connection
from typing import Type
from jinja2 import Markup
from numpy import number
import quantum_game_web as quantum_game

from flask import g, Flask, render_template, redirect, request, session, jsonify
import flask
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, emit, join_room, leave_room, close_room, rooms, disconnect



app = Flask(__name__, static_url_path='/static')
socketio = SocketIO(app, async_mode=None)
games = {}

# EXAMPLE: CHANGE THIS BEFORE USE
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

# ----------------------------------------------

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return quantum_game.Player.get(user_id)

@app.route('/login', methods=['GET', 'POST'])
def login():
    
    if request.form and request.method == 'POST':
        print("post")
        user = load_user(request.form['username'])
        print(user)
        login_user(user)

        flask.flash('Logged in successfully.')

        return redirect("/")
    return render_template('login.html', Player=f"Player {len(quantum_game.Player.players) + 1}")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")

def authenticated_only(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            disconnect()
        else:
            return f(*args, **kwargs)
    return wrapped

# ----------------------------------------------

@app.route('/')
def hello():
    return render_template('home.html')

@app.route('/test')
def test():
    return app.send_static_file("basicUsage.html")


# ----------------------------------------------

### Game Code/API

def get_game(lobby) -> quantum_game.Game:
    return get_games().get(lobby)

def get_games():
    if 'games' not in g:
        global games
        g.games = games
    return g.games


@app.route('/create_game', methods=['GET', 'POST'])
@login_required
def create_game():
    if request.form and request.method == 'POST':
        lobby = request.form['lobby_name']
        print(games)
        games[lobby] = quantum_game.Game()
        flask.flash('Created Game Successfully')

        return redirect(f"/game/{lobby}")
    
    return render_template('create_game.html')

@app.route('/game/<lobby>')
def access_lobby(lobby):
    game = get_game(lobby)
    if not game: return redirect('/create_game')
    
    map = get_map(lobby)
    if not map:     return render_template("game.html", 
                           lobby=lobby)
    return render_template("game.html", 
                           lobby=lobby, 
                        #    nodes=map['nodes'], 
                        #    connections=map['connections']
                           )
    
def get_map(lobby):
    game = get_game(lobby)
    map = {"nodes": game.get_map().get_nodes(), 
           "connections": game.get_map().get_connections()}
    # print(map)
    return map

def request_choices(lobby, player):
    game = get_game(lobby)
    choices, phase = game.get_action_requests(player)
    return {'data': choices, 'phase': phase}#, 'number': number}


@socketio.event
@authenticated_only
def join(data):
    username: quantum_game.Player = current_user
    lobby = data['lobby']
    game = get_game(lobby)
    if not game: return redirect('/create_game')
    game.add_player(current_user)
    print(f"{username}, {lobby} - Joined")
    join_room(lobby)
    emit("players", game.get_players_list(), to=lobby)
    if game.is_running():
        update_lobby(lobby)
        get_choices(lobby, username)
    elif game.is_initialised():
        game.run_remote()
        update_lobby(lobby)
        get_choices(lobby, username)

def update_lobby(lobby):
    game = get_game(lobby)
    emit("update_lobby", {'turn': game.turns}, to=lobby)

@socketio.event
@authenticated_only
def update_choices(lobby):
    get_choices(lobby, current_user.id)

@socketio.event
@authenticated_only
def update_map(lobby):
    emit("update_map", get_map(lobby))
    get_choices(lobby, current_user)

def get_choices(lobby, user):
    choices = request_choices(lobby, user.id)
    print(choices)
    emit("get_choices", choices)
    
@socketio.event
@authenticated_only
def select(data):
    print(f"{current_user} - {data}")
    game = get_game(data['lobby'])
    next_phase = game.set_action_requests(current_user.id, data['data'])
    
    if next_phase:
        update_lobby(data['lobby'])
    
        
# @socketio.event
# @authenticated_only
# def get_requests(data):
#     print('get_requests')
#     lobby = data['lobby']
#     # emit()

# ----------------------------------------------

if __name__ == '__main__':
    socketio.run(app, debug=True, use_reloader=True)
    session.clear()