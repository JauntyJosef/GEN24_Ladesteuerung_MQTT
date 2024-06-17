import paho.mqtt.client as mqtt
import configparser
import json
import time

EV_Reservierung = '/home/GEN24/html/EV_Reservierung.json'
Entladesteuerfile = 'Akku_EntLadeSteuerFile.json'
Watt_Reservierungsfile = 'Watt_Reservierung.json'

config = configparser.ConfigParser()
config.read('/home/GEN24/config.ini')

broker_address = config.get('MQTT', 'broker_address')
broker_port = config.getint('MQTT', 'broker_port')
maintopic = config.get('MQTT', 'maintopic')

message_received = False

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Verbunden mit MQTT Broker: ", broker_address)
        client.subscribe(userdata['topic'])
    else:
        print("Verbindung fehlgeschlagen, Fehlercode =", rc)

def on_publish(client, userdata, mid):
    print("Nachricht erfolgreich veröffentlicht.")

def on_message(client, userdata, msg):
    global message_received
    print("Nachricht empfangen: ", msg.topic, ": ", msg.payload.decode(), "\n")
    userdata['message'] = msg.payload.decode()
    message_received = True
    client.disconnect()

def publish_message(topic, payload):
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_publish = on_publish

    client.connect(broker_address, broker_port)
    client.publish(topic, payload, retain=True)
    client.disconnect()

def subscribe_to_topic(topic):
    global message_received
    message_received = False
    userdata = {'message': None, 'topic': topic}
    client = mqtt.Client(userdata=userdata)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(broker_address, broker_port)
    client.loop_start()

    timeout = 5  # Sekunden
    start_time = time.time()

    while not message_received and (time.time() - start_time) < timeout:
        time.sleep(0.1)

    client.loop_stop()

    if not message_received:
        print()
        print(f"Fehler: Keine Nachricht auf dem Topic {topic} innerhalb von {timeout} Sekunden empfangen.")
        return None

    return userdata['message']

# Funktion zum Laden der JSON-Datei EV_Reservierung
def lade_json(datei):
    with open(datei, 'r') as f:
        daten = json.load(f)
    return daten

# Funktion zum Speichern der JSON-Datei EV_Reservierung
def speichere_json(daten, datei):
    with open(datei, 'w') as f:
        json.dump(daten, f, indent=4)

def lesen():
    Entladerate = subscribe_to_topic(maintopic + "/Entladerate")
    Laderate = subscribe_to_topic(maintopic + "/Laderate")
    daten = lade_json(EV_Reservierung)
    daten2 = lade_json(Watt_Reservierungsfile)
    daten3 = lade_json(Entladesteuerfile)
    
    # EV_Reservierung und Watt_Reservierung
    laderate_map = {
        "Auto": ("0", 0),
        "Aus": ("0.000001", 0.001),
        "Halb": ("0.0005", 0.5),
        "Voll": ("0.001", 1)
    }   
    # Überprüfen, ob Laderate in der Zuordnungstabelle existiert
    if Laderate in laderate_map:
        # Laderate-Werte aus der Zuordnungstabelle erhalten
        res_feld1, manuelle_steuerung = laderate_map[Laderate]
        
        # Werte setzen und JSON speichern
        daten['ManuelleSteuerung']['Res_Feld1'] = res_feld1
        daten2['ManuelleSteuerung'] = manuelle_steuerung
        speichere_json(daten, EV_Reservierung)
        speichere_json(daten2, Watt_Reservierungsfile)
    else:
        print("Fehler beim Schreiben in EV_Reservierung.")

    # Akku_Entladesteuerfile
    try:
        Entladerate = int(Entladerate)
        if 0 <= Entladerate <= 100:
            step = 20
            for i in range(0, 101, step):
                if i <= Entladerate < i + step:
                    daten3['ManuelleEntladesteuerung']['Res_Feld1'] = i
                    speichere_json(daten3, Entladesteuerfile)
                    break
        else:
            print("Fehler beim Schreiben in Entladesteuerfile.")
    except ValueError:
        print("Fehler beim Konvertieren der Entladerate.")

