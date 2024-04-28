import sys
import mqtt_functions
import configparser

config = configparser.ConfigParser()
config.read('/home/GEN24/config.ini')
maintopic = config.get('MQTT', 'maintopic')

# Überprüfe, ob die Anzahl der übergebenen Argumente korrekt ist
if len(sys.argv) != 2:
    print("Bitte geben Sie genau ein Argument an.")
    sys.exit(1)

# Die Variable aus dem ersten Argument lesen (das Skript selbst ist argv[0])
Wert = sys.argv[1]

# Überprüfe den Wert der Variable und führe entsprechende Aktionen aus
if Wert == "0":
    value = "Auto"
    mqtt_functions.publish_message(maintopic + "/Laderate", value)
    # Hier kannst du Code für Fall 1 einfügen
elif Wert == "0.000001":
    value = "Aus"
    mqtt_functions.publish_message(maintopic + "/Laderate", value)
elif Wert == "0.0005":
    value = "Halb"
    mqtt_functions.publish_message(maintopic + "/Laderate", value)
elif Wert == "0.001":
    value = "Voll"
    mqtt_functions.publish_message(maintopic + "/Laderate", value)
elif Wert == "AUS":
    value = "0"
    mqtt_functions.publish_message(maintopic + "/Entladerate", value)
else:
    value = Wert
    mqtt_functions.publish_message(maintopic + "/Entladerate", value)




