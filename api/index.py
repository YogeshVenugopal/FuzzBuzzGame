from flask import Flask, render_template, request

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/game")
def about():
    return render_template("game.html")
# Required for Vercel
def handler(event, context):
    return app(event, context)