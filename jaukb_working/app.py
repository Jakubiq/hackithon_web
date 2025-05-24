import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import folium_static
import pandas as pd
import os
import plotly.express as px
import hashlib # Pro hashování

st.set_page_config(layout="wide") # Pro širší layout aplikace
st.title("Pokrytí dálnic mobilním signálem")

# --- Vlastní hashovací funkce pro GeoDataFrame ---
# Streamlit potřebuje vědět, jak zahashovat GeoDataFrame pro cachování.
# Hashujeme data (DataFrame část) a geometrii zvlášť.
def hash_geodataframe(gdf):
    if not isinstance(gdf, gpd.GeoDataFrame):
        raise TypeError("Expected a GeoDataFrame for hashing.")
    
    # Hashování datové části (bez geometrie)
    # Používáme errors='ignore' pro případ, že by geometrický sloupec nebyl nalezen (i když by měl být)
    df_hash = hashlib.sha256(pd.util.hash_pandas_object(gdf.drop(columns=[gdf.geometry.name], errors='ignore')).values).hexdigest()
    
    # Hashování geometrické části
    geometry_hash = hashlib.sha256(pd.util.hash_pandas_object(gdf.geometry).values).hexdigest()
    
    return f"{df_hash}-{geometry_hash}"

# Načítání dat o dálnicích
dalnice_framy = []
seznam_dalnic = [0, 1, 2, 3, 4, 5, 6, 8, 10, 11, 35, 46, 52, 55]

# Použijeme st.cache_data pro načítání dat dálnic
@st.cache_data(hash_funcs={gpd.GeoDataFrame: hash_geodataframe})
def load_all_dalnice_data(seznam_dalnic_param): # Změnil jsem název parametru, aby se vyhnul kolizi s globální proměnnou
    all_dfs = []
    for i in seznam_dalnic_param:
        file_path = f"./dalnice/pokryti-dalnic-mobilnim-signalem-d{i}_converted.geojson"
        if os.path.exists(file_path):
            df = gpd.read_file(file_path)
            df['dalnice'] = f"D{i}" # Identifikace dálnice
            all_dfs.append(df)
        else:
            st.warning(f"Soubor s daty pro D{i} nebyl nalezen: {file_path}")
    if all_dfs:
        return pd.concat(all_dfs)
    return gpd.GeoDataFrame() # Vrať prázdný GeoDataFrame, pokud se nic nenačte

dalnice_celek = load_all_dalnice_data(seznam_dalnic)

# Načítání overlay souborů (obce, kraje atd.)
overlays_files = os.listdir("./overlays") 

total_overlays = []
overlays_names = []
kraje_gdf = None
# Pevně nastavíme název sloupce pro kraje na "NAZEV" podle tvého GEOJSONu
kraje_nazev_sloupce = "NAZEV" 

# Použijeme st.cache_data pro načítání overlay dat
@st.cache_data(hash_funcs={gpd.GeoDataFrame: hash_geodataframe})
def load_all_overlays(overlays_files_param, kraje_nazev_sloupce_param):
    all_overlays_list = []
    names_list = []
    kraje_g = None
    
    for file in overlays_files_param:
        file_path = f"./overlays/{file}"
        if os.path.exists(file_path):
            gdf = gpd.read_file(file_path)
            all_overlays_list.append(gdf)
            names_list.append(file.split("_")[0]) 

            if "VUSC_P.shp.geojson" in file:
                kraje_g = gdf
                st.sidebar.info(f"Identifikovaný sloupec pro název kraje: **{kraje_nazev_sloupce_param}** v souboru {file}")
        else:
            st.warning(f"Soubor s overlay daty nebyl nalezen: {file_path}")
    return all_overlays_list, names_list, kraje_g

total_overlays, overlays_names, kraje_gdf = load_all_overlays(overlays_files, kraje_nazev_sloupce)

# Map_data_file pro obecný popup může být stále užitečný
# Ověřte, že soubor existuje, než ho načtete
map_data_file_path = "./overlays/VUSC_P.shp.geojson"
if os.path.exists(map_data_file_path):
    map_data_file = gpd.read_file(map_data_file_path)
else:
    st.error(f"Chybí soubor pro map data: {map_data_file_path}. Popupy pro overlaye nemusí fungovat správně.")
    map_data_file = gpd.GeoDataFrame() # Prázdný GDF, aby se kód nerozbil


operatori = {
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

# --- Funkce pro přípravu dat o krajích pro popupy ---
# Nyní s custom hash_funcs pro GeoDataFrame
@st.cache_data(hash_funcs={gpd.GeoDataFrame: hash_geodataframe})
def prepare_kraje_data_for_popup(data_dalnice, data_kraje, nazev_sloupce_kraje):
    if data_kraje is None or data_kraje.empty or nazev_sloupce_kraje not in data_kraje.columns:
        st.warning(f"Data krajů nejsou k dispozici nebo chybí sloupec '{nazev_sloupce_kraje}'. Informace o krajích nebudou v popupech.")
        return None # Vracíme None, pokud data nejsou platná

    # Převedeme CRS dálnic na CRS krajů
    if not data_dalnice.empty:
        # Zkontrolujeme, zda se CRS liší, než provedeme transformaci
        if data_dalnice.crs != data_kraje.crs:
            data_dalnice_proj = data_dalnice.to_crs(data_kraje.crs)
        else:
            data_dalnice_proj = data_dalnice
    else:
        st.warning("Data dálnic jsou prázdná, nelze provést prostorové spojení s kraji.")
        return data_kraje.copy() # Vrátíme kopii krajů bez dalších dat

    # Spojení dálnic s kraji na základě prostorového umístění
    dalnice_v_krajich = gpd.sjoin(data_dalnice_proj, data_kraje, how="inner", predicate="within")

    if dalnice_v_krajich.empty:
        st.warning("Žádné body dálnic se nepřekrývají s kraji. Zkontrolujte CRS a geometrie.")
        return data_kraje.copy()

    for op_name, op_col in operatori.items():
        dalnice_v_krajich[f"{op_name}_quality"] = dalnice_v_krajich[op_col].apply(get_quality)

    # Vytvoříme kopii data_kraje, abychom neměnili cachovaný objekt přímo
    kraje_s_daty = data_kraje.copy()

    # Vypočítáme podíl dobrého signálu pro každého operátora v každém kraji
    for kraj_idx, kraj_row in kraje_s_daty.iterrows():
        kraj_name = kraj_row[nazev_sloupce_kraje]
        kraj_data = dalnice_v_krajich[dalnice_v_krajich[nazev_sloupce_kraje] == kraj_name]
        
        total_points_in_kraj = len(kraj_data)
        
        op_info_html = f"<b>Kraj: {kraj_name}</b><br><br>Statistiky signálu:<br>"
        best_op_name = "N/A"
        max_perc = -1.0
        
        if total_points_in_kraj > 0:
            operator_percentages = []
            for op_name in operatori.keys():
                good_signal_points = len(kraj_data[kraj_data[f"{op_name}_quality"] == "dobrý"])
                percentage_good = (good_signal_points / total_points_in_kraj) * 100
                operator_percentages.append((op_name, percentage_good))
                op_info_html += f"&nbsp;&nbsp;&nbsp;&nbsp;{op_name}: {percentage_good:.1f}% dobrého signálu<br>"
            
            # Najdeme nejlepšího operátora pro tento kraj
            if operator_percentages:
                best_op_name, max_perc = max(operator_percentages, key=lambda item: item[1])
            
            op_info_html += f"<br><b>Nejlepší operátor na dálnici: {best_op_name} ({max_perc:.1f}% dobrého signálu)</b>"

        else:
            op_info_html += "Žádná data o signálu v tomto kraji."

        # Přidáme HTML řetězec do nové vlastnosti GeoDataFrame
        kraje_s_daty.loc[kraj_idx, 'popup_html'] = op_info_html
            
    return kraje_s_daty

# --- Hlavní část aplikace Streamlit ---

if not dalnice_celek.empty:

    # Předzpracujeme data o krajích s informacích o signálu
    prepared_kraje_gdf = prepare_kraje_data_for_popup(dalnice_celek, kraje_gdf, kraje_nazev_sloupce)


    operator = st.radio(
        "Vyberte operátora",
        list(operatori.keys())
    )
    operator_col = operatori[operator]

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
        index = 0 
    )
    if precision == "Větší přesnost (každý 10. bod)":
        reduction_factor = 10
    elif precision == "Menší přesnost (každý 20. bod)":
        reduction_factor = 20
    else:
        reduction_factor = 1 

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
        st.warning("Pro vybraného operátora a kvalitu signálu nejsou v datech žádné body k zobrazení na mapě.")
    else:
        # Základní nastavení mapy
        fig = folium.Figure(width=1200, height=1200)

        m = folium.Map(
            location=[50.0716968, 14.444761], # Ústí nad Labem
            zoom_start=8,
        ).add_to(fig)

        folium.plugins.Fullscreen(
            position="topright",
            title="Fullscreen",
            title_cancel="Zmenšit",
            forced_separate_button=True,
        ).add_to(m)

        # 1. Přidání vrstvy pro kraje (spodní vrstva)
        if prepared_kraje_gdf is not None and not prepared_kraje_gdf.empty:
            folium.GeoJson(
                prepared_kraje_gdf,
                name="Kraje (statistiky)",
                style_function=lambda feature: {
                    'fillColor': 'lightblue',
                    'color': 'black',
                    'weight': 1,
                    'fillOpacity': 0.5,
                },
                highlight_function=lambda x: {
                    'fillColor': '#00F0F0',
                    'color': 'black',
                    'fillOpacity': 0.7,
                    'weight': 3
                },
                popup=folium.GeoJsonPopup(
                    fields=['popup_html'],
                    aliases=[''],
                    localize=True,
                    max_width=400, 
                    show_name=False
                )
            ).add_to(m)
        else:
            st.warning("Data pro vrstvu krajů s popupy nejsou k dispozici.")

        # 2. Přidání bodů na dálnici (horní vrstva, přes kraje)
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
                radius=150, 
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
            
        folium.LayerControl().add_to(m)

        folium_static(m)
else:
    st.error("Nepodařilo se načíst žádná data o dálnicích. Zkontrolujte cestu k souborům.")