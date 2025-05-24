import os

overlays_files = os.listdir("./overlays") # Budeme doufat, ze kazdy druh overlaye zacina tim jmenem, kterym jakoby je ve skutecnosti

total_overlays = []
for file in overlays_files:
    overlays_names = file.split("_")[0] 
    total_overlays.append(file.split("_")[0])

print(total_overlays)