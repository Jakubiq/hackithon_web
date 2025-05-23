import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import folium_static

dalnice_file = gpd.read_file("./dalnice/pokryti-dalnic-mobilnim-signalem-d8_converted.geojson") 
map_data_file = st.file_uploader("Nahrajte GeoJSON soubor", type=["geojson", "json"])

if st.button("Klikni"): 
    map_data_file_geo = gpd.read_file(map_data_file)

    # Streamlit titulek
    st.title("Interaktivní mapa okresů ČR (klikací)")

    # Vytvoření mapy
    m = folium.Map(location=[49.8, 15.5], zoom_start=7)

    # Přidání GeoJSON vrstvy s popup (klikací) a highlight (zvýraznění po kliknutí)
    folium.GeoJson(
        map_data_file_geo,
        name="Okresy",
        style_function=lambda feature: {
            'fillColor': 'lightblue',
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.5,
        },
        highlight_function=lambda feature: {
            'weight': 4,
            'color': 'red',
            'fillOpacity': 0.7
        },
        popup=folium.GeoJsonPopup(
            fields=[map_data_file_geo.columns[0]],  # Např. ["NAZ_OKRES"]
            aliases=["Okres:"],
            localize=True
        )
    ).add_to(m)

    # Ovládání vrstev
    folium.LayerControl().add_to(m)

    # Zobrazení mapy ve Streamlit
    folium_static(m)