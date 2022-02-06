from jinja2 import Markup
import quantum_game

from flask import Flask, render_template

app = Flask(__name__, static_url_path='/static')
game: quantum_game.Game = None

@app.route('/')
def hello():
    return render_template('home.html')

@app.route('/test')
def test():
    return app.send_static_file("basicUsage.html")



### Game Code/API

@app.route('/game')
def game():
    global game
    game = quantum_game.Game([quantum_game.Player("Cal"), 
                              quantum_game.Player("bot")
                              ], quantum_game.map_test)
    # game.run()
    
    return render_template("game.html", nodes=Markup(game.map.get_nodes()), connections=Markup(game.map.get_connections()))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
