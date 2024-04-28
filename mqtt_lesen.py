import mqtt_functions
import json
import configparser

EV_Reservierung = '/home/GEN24/html/EV_Reservierung.json'
Entladesteuerfile = 'Akku_EntLadeSteuerFile.json'

config = configparser.ConfigParser()
config.read('/home/GEN24/config.ini')
maintopic = config.get('MQTT', 'maintopic')

# Funktion zum Laden der JSON-Datei EV_Reservierung
def lade_json(EV_Reservierung):
    with open(EV_Reservierung, 'r') as f:
        daten = json.load(f)
    return daten

# Funktion zum Speichern der JSON-Datei EV_Reservierung
def speichere_json(daten, EV_Reservierung):
    with open(EV_Reservierung, 'w') as f:
        json.dump(daten, f, indent=4)


def lesen():
    Entladerate = mqtt_functions.subscribe_to_topic(maintopic + "/Entladerate")
    Laderate = mqtt_functions.subscribe_to_topic(maintopic + "/Laderate")

    # Laden der JSON-Daten
    daten = lade_json(EV_Reservierung)
    # Überprüfung des Werts
    if Laderate == "Auto":
        #print(f"Laderate: {Laderate}")
        daten['ManuelleSteuerung']['Res_Feld1'] = "0"
        speichere_json(daten, EV_Reservierung)
        #print("Änderung erfolgreich durchgeführt.")
    elif Laderate == "Aus":
        #print(f"Laderate: {Laderate}")
        daten['ManuelleSteuerung']['Res_Feld1'] = "0.000001"
        speichere_json(daten, EV_Reservierung)
        #print("Änderung erfolgreich durchgeführt.")
    elif Laderate == "Halb":
        #print(f"Laderate: {Laderate}")
        daten['ManuelleSteuerung']['Res_Feld1'] = "0.0005"
        speichere_json(daten, EV_Reservierung)
        #print("Änderung erfolgreich durchgeführt.")
    elif Laderate == "Voll":
        #print(f"Laderate: {Laderate}")
        daten['ManuelleSteuerung']['Res_Feld1'] = "0.001"
        speichere_json(daten, EV_Reservierung)
        #print("Änderung erfolgreich durchgeführt.")
    else:
        print("Fehler beim Schreiben in EV_Reservierung.")

    # Laden der JSON-Daten
    daten = lade_json(Entladesteuerfile)
    if 0 <= int(Entladerate) < 20:
        daten['ManuelleEntladesteuerung']['Res_Feld1'] = 0
        speichere_json(daten, Entladesteuerfile)
    elif 20 <= int(Entladerate) < 39:
        daten['ManuelleEntladesteuerung']['Res_Feld1'] = 20
        speichere_json(daten, Entladesteuerfile)
    elif 40 <= int(Entladerate) < 59:
        daten['ManuelleEntladesteuerung']['Res_Feld1'] = 40
        speichere_json(daten, Entladesteuerfile)
    elif 60 <= int(Entladerate) < 79:
        daten['ManuelleEntladesteuerung']['Res_Feld1'] = 60
        speichere_json(daten, Entladesteuerfile)
    elif 80 <= int(Entladerate) <= 99:
        daten['ManuelleEntladesteuerung']['Res_Feld1'] = 80
        speichere_json(daten, Entladesteuerfile)
    elif int(Entladerate) == 100:
        daten['ManuelleEntladesteuerung']['Res_Feld1'] = 100
        speichere_json(daten, Entladesteuerfile)
    else:
        print("Fehler beim Schreiben in Entladesteuerfile.")
