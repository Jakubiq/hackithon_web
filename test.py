import os

overlays_files = os.listdir("./overlays") # Budeme doufat, ze kazdy druh overlaye zacina tim jmenem, kterym jakoby je ve skutecnosti

total_overlays = []
for file in overlays_files:
    total_overlays.append(gpd.read_file(f"./overlays/{file}"))
    overlays_names = i.split("_")[0] 

print(overlays_names)