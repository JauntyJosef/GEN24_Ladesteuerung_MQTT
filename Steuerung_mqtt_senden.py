import sys
import mqtt_functions
import configparser


config = configparser.ConfigParser()
config.read('/home/GEN24/config.ini')
maintopic = config.get('MQTT', 'maintopic')
control_topic = config.get('MQTT', 'control_topic')
MQTT = config.get('MQTT', 'mqtt')

if MQTT == 1:
    if len(sys.argv) != 2:
        print("Bitte geben Sie genau ein Argument an.")
        sys.exit(1)

    Wert = sys.argv[1]

    mqtt_functions.publish_message(maintopic + "/" + control_topic, Wert)