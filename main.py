from flask import Flask
import geopandas
from streamlit_foliom import st_folium
import streamlit as st

app = Flask(__name__)

@app.route("/")
def home():
    return "Ahoj, světe!"

st.title("Vizualizace mapy a GEOJson dat")
fileGJ = st.file_uploader 

if __name__ == "__main__":
    app.run(debug=True)
