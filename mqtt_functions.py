import paho.mqtt.client as mqtt
import configparser

config = configparser.ConfigParser()
config.read('/home/GEN24/config.ini')

broker_address = config.get('MQTT', 'broker_address')
broker_port = config.getint('MQTT', 'broker_port')

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
