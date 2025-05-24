import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import folium_static
import pandas as pd

st.title("Interaktivní mapa signálu na dálnici")

dalnice_framy = []
seznam_dalnic = [0, 1, 2, 3, 4, 5, 6, 8, 10, 11, 35, 46, 52, 55]
for i in range(0, 57):
    if i in seznam_dalnic:
        dalnice_framy.append(gpd.read_file(f"./dalnice/pokryti-dalnic-mobilnim-signalem-d{i}_converted.geojson"))
map_data_file = st.file_uploader("Nahrajte GeoJSON soubor", type=["geojson", "json"])

dalnice_celek = pd.concat(dalnice_framy)

# Chci aby to vzalo vsechny soubory v dalnice a z nich to vyzobrazilo tu mapu - cyklus? 

operator_map = {
    "T-Mobile LTE": "T-Mobile LTE - RSRP",
    "O2 LTE": "O2 LTE - RSRP",
    "Vodafone LTE": "Vodafone LTE - RSRP"
}

signal_quality_ranges = {
    "dobrý": (-70, 0),
    "střední": (-85, -70),
    "špatný": (-120, -85)
}

signal_quality_colors = {
    "dobrý": "green",
    "střední": "orange",
    "špatný": "red"
}

quality_options = ["všechny"] + list(signal_quality_ranges.keys())

def get_quality(value):
    if value >= signal_quality_ranges["dobrý"][0]:
        return "dobrý"
    elif value >= signal_quality_ranges["střední"][0]:
        return "střední"
    else:
        return "špatný"

if dalnice_celek is not None:

    operator = st.radio(
        "Vyberte operátora",
        list(operator_map.keys())
    )
    operator_col = operator_map[operator]

    quality = st.selectbox(
        "Vyberte kvalitu signálu",
        quality_options
    )

    precision_options = [
        "Menší přesnost (každý 20. bod)",
        "Větší přesnost (každý 10. bod)",
        "Maximální přesnost (všechny body 1:1)",

    ]
    precision = st.radio(
        "Zvolte přesnost zobrazení",
        precision_options,
        index = 0 # Výchozí je větší přesnost (každý 10. bod)
    )
    if precision == "Větší přesnost (každý 10. bod)":
        reduction_factor = 10
    elif precision == "Menší přesnost (každý 20. bod)":
        reduction_factor = 20
    else:
        reduction_factor = 1  # všechny body

    filtered_dalnice = dalnice_celek[~dalnice_celek[operator_col].isna()]

    if quality == "všechny":
        filtered_dalnice = filtered_dalnice.copy()
        filtered_dalnice["signal_quality"] = filtered_dalnice[operator_col].apply(get_quality)
        st.write(f"Počet bodů s dostupným signálem {operator}: {len(filtered_dalnice)}")
    else:
        min_val, max_val = signal_quality_ranges[quality]
        filtered_dalnice = filtered_dalnice[(filtered_dalnice[operator_col] >= min_val) & (filtered_dalnice[operator_col] < max_val)]
        st.write(f"Počet bodů s dostupným signálem {operator} a kvalitou '{quality}': {len(filtered_dalnice)}")

    # Redukce počtu bodů
    redukovane_body = filtered_dalnice.iloc[::reduction_factor, :]

    st.write(f"Zobrazeno bodů po redukci: {len(redukovane_body)}")

    if redukovane_body.empty:
        st.warning("Pro vybraného operátora a kvalitu signálu nejsou v datech žádné body.")
    else:
        fig = folium.Figure(width=1200, height=1200)
        m = folium.Map(
            location=[50.0716968, 14.444761],
            zoom_start=8,
        ).add_to(fig)
        for _, row in redukovane_body.iterrows():
            signal = row[operator_col]
            time = row.get('time', 'N/A')
            if quality == "všechny":
                color = signal_quality_colors[row["signal_quality"]]
            else:
                color = signal_quality_colors[quality]
            # Průhledný větší kruh (dosah signálu)
            folium.Circle(
                location=[row.geometry.y, row.geometry.x],
                radius=150,  # v metrech, uprav dle potřeby
                color=None,
                fill=True,
                fill_color=color,
                fill_opacity=0.15,
                popup=None
            ).add_to(m)
            # Malý bod
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=5,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7,
                popup=f"{operator}: {signal} dBm<br>Čas: {time}"
            ).add_to(m)
        folium_static(m)
