from flask import Flask, render_template

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/game")
def game():
    return render_template("game.html")

@app.route("/favicon.ico")
def favicon():
    return "", 204