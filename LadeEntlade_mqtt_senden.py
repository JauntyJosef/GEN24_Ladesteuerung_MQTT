import sys
import mqtt_functions
import configparser


config = configparser.ConfigParser()
config.read('/home/GEN24/config.ini')
maintopic = config.get('MQTT', 'maintopic')
MQTT = config.get('MQTT', 'mqtt')

if MQTT == 1:
    if len(sys.argv) != 2:
        print("Bitte geben Sie genau ein Argument an.")
        sys.exit(1)

    Wert = sys.argv[1]

    if Wert == "AUS":
        topic = maintopic + "/Entladerate"
        value = "0"
    elif Wert == "0":
        topic = maintopic + "/Laderate"
        value = "Auto"
    elif Wert == "0.000001":
        topic = maintopic + "/Laderate"
        value = "Aus"
    elif Wert == "0.0005":
        topic = maintopic + "/Laderate"
        value = "Halb"
    elif Wert == "0.001":
        topic = maintopic + "/Laderate"
        value = "Voll"
    else:
        topic = maintopic + "/Entladerate"
        value = Wert

    mqtt_functions.publish_message(topic, value)