from flask import Flask
import geopandas

app = Flask(__name__)

@app.route("/")
def home():
    return "Ahoj, světe!"

if __name__ == "__main__":
    app.run(debug=True)
