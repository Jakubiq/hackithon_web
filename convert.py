import streamlit as st
import pandas as pd
import geojson # Knihovna pro tvorbu GeoJSON objektů
import io # Pro práci se soubory v paměti

st.title("Převodník CSV na GeoJSON")

st.write("""
Nástroj pro převod CSV souboru obsahujícího souřadnice do formátu GeoJSON (body).
Váš CSV soubor by měl obsahovat sloupce se zeměpisnou šířkou a délkou.
Názvy sloupců pro souřadnice by měly být 'LAT' a 'LON' (nebo 'latitude' a 'longitude').
Desetinná čísla v CSV by měla používat čárku jako oddělovač (např. 50,12345).
""")

uploaded_file_csv = st.file_uploader("1. Nahrajte CSV soubor", type=["csv"])

if uploaded_file_csv is not None:
    try:
        # Načtení CSV souboru pomocí pandas
        # Specifikujeme oddělovač ';' a desetinnou čárku ','
        # Také se pokusíme detekovat kódování, běžné je 'utf-8' nebo 'windows-1250' pro české soubory
        try:
            df = pd.read_csv(uploaded_file_csv, delimiter=';', decimal=',')
            st.success(f"CSV soubor '{uploaded_file_csv.name}' úspěšně načten (kódování UTF-8).")
        except UnicodeDecodeError:
            st.info("Nepodařilo se načíst s UTF-8, zkouším windows-1250...")
            uploaded_file_csv.seek(0) # Vrátíme se na začátek souboru pro nové čtení
            df = pd.read_csv(uploaded_file_csv, delimiter=';', decimal=',', encoding='windows-1250')
            st.success(f"CSV soubor '{uploaded_file_csv.name}' úspěšně načten (kódování windows-1250).")

        st.subheader("Náhled prvních 5 řádků CSV:")
        st.dataframe(df.head())

        # Identifikace sloupců pro latitude a longitude
        lat_col = None
        lon_col = None

        possible_lat_cols = ['LAT', 'latitude', 'Latitude', 'lat']
        possible_lon_cols = ['LON', 'longitude', 'Longitude', 'lon']

        for col in possible_lat_cols:
            if col in df.columns:
                lat_col = col
                break
        
        for col in possible_lon_cols:
            if col in df.columns:
                lon_col = col
                break

        if lat_col is None or lon_col is None:
            st.error(f"Nepodařilo se najít sloupce pro zeměpisnou šířku (očekávané názvy: {possible_lat_cols}) "
                       f"a/nebo délku (očekávané názvy: {possible_lon_cols}) v CSV. "
                       f"Nalezené sloupce: {list(df.columns)}")
        else:
            st.info(f"Používám sloupec '{lat_col}' pro zeměpisnou šířku a '{lon_col}' pro zeměpisnou délku.")

            features = []
            for index, row in df.iterrows():
                try:
                    # Získání souřadnic a vlastností
                    # GeoJSON vyžaduje pořadí [longitude, latitude]
                    point_geometry = geojson.Point((float(row[lon_col]), float(row[lat_col])))
                    
                    # Všechny ostatní sloupce z CSV se stanou vlastnostmi (properties)
                    properties = row.to_dict()
                    # Odstraníme lat a lon z properties, protože už jsou v geometrii
                    if lat_col in properties:
                        del properties[lat_col]
                    if lon_col in properties:
                        del properties[lon_col]
                    
                    feature = geojson.Feature(geometry=point_geometry, properties=properties)
                    features.append(feature)
                except ValueError as ve:
                    st.warning(f"Řádek {index+2}: Nepodařilo se převést souřadnice na čísla ({row[lon_col]}, {row[lat_col]}). Chyba: {ve}. Tento řádek bude přeskočen.")
                    continue # Přeskočíme tento řádek a pokračujeme s dalšími
                except Exception as e_row:
                    st.warning(f"Řádek {index+2}: Neočekávaná chyba při zpracování: {e_row}. Tento řádek bude přeskočen.")
                    continue


            if not features:
                st.error("Nepodařilo se vytvořit žádné GeoJSON prvky. Zkontrolujte formát souřadnic v CSV.")
            else:
                # Vytvoření GeoJSON FeatureCollection
                feature_collection = geojson.FeatureCollection(features)

                # Převod GeoJSON objektu na řetězec
                geojson_string = geojson.dumps(feature_collection, indent=2) # indent pro hezčí formátování

                st.subheader("Vygenerovaný GeoJSON (prvních 1000 znaků):")
                st.code(geojson_string[:1000] + "...", language='json')

                # Nabídnutí GeoJSON souboru ke stažení
                st.download_button(
                    label="2. Stáhnout GeoJSON soubor",
                    data=geojson_string,
                    file_name=f"{uploaded_file_csv.name.split('.')[0]}_converted.geojson",
                    mime="application/geo+json"
                )
                st.success("GeoJSON úspěšně vygenerován!")

    except pd.errors.ParserError as pe:
        st.error(f"Chyba při parsování CSV souboru: {pe}. Ujistěte se, že oddělovač je ';' a desetinná čárka ','.")
    except Exception as e:
        st.error(f"Došlo k neočekávané chybě při zpracování CSV souboru:")
        st.exception(e)
else:
    st.info("Nahrajte CSV soubor pro převod na GeoJSON.")

