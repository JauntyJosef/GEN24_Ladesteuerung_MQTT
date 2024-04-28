import paho.mqtt.client as mqtt
import configparser
import json

EV_Reservierung = '/home/GEN24/html/EV_Reservierung.json'
Entladesteuerfile = 'Akku_EntLadeSteuerFile.json'

config = configparser.ConfigParser()
config.read('/home/GEN24/config.ini')

broker_address = config.get('MQTT', 'broker_address')
broker_port = config.getint('MQTT', 'broker_port')
maintopic = config.get('MQTT', 'maintopic')

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Verbunden mit MQTT Broker: ",broker_address)
    else:
        print("Verbindung fehlgeschlagen, Fehlercode =", rc)

def on_publish(client, userdata, mid):
    print("Nachricht erfolgreich veröffentlicht.")

def on_message(client, userdata, msg):
    print("Nachricht empfangen: ", msg.topic, ": ",msg.payload.decode(),"\n")
    #print("Wert:", msg.payload.decode())

    # Hier könntest du die Nachricht speichern oder zurückgeben, je nach Bedarf
    userdata['message'] = msg.payload.decode()

    # Verbindung trennen
    client.disconnect()

def publish_message(topic, payload):
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_publish = on_publish

    client.connect(broker_address, broker_port)
    client.publish(topic, payload, retain=True)
    client.disconnect()

def subscribe_to_topic(topic):
    userdata = {'message': None}  # Initialisiere einen leeren 'message'-Schlüssel in userdata
    client = mqtt.Client(userdata=userdata)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(broker_address, broker_port)
    client.subscribe(topic)
    client.loop_forever()  # Wartet auf eingehende Nachrichten und ruft die Callback-Funktion on_message auf
    
    return userdata['message']  # Gibt die empfangene Nachricht zurück

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
    Entladerate = subscribe_to_topic(maintopic + "/Entladerate")
    Laderate = subscribe_to_topic(maintopic + "/Laderate")

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

