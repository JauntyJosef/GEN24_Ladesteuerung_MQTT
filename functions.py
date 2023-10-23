# Funktionen für die Gen24_Ladesteuerung
from datetime import datetime
import json
import configparser

def loadConfig(conf_file):
        # Damit die Variable config auch in der Funktion "getVarConf" vorhanden ist (global config)
        global config
        config = configparser.ConfigParser()
        try:
                config.read_file(open(conf_file))
                config.read(conf_file)
        except:
                print('ERROR: config file not found.')
                exit(0)
        return config

def loadWeatherData(weatherfile):
        data = None
        try:
            with open(weatherfile) as json_file:
                data = json.load(json_file)
        except:
                print("Wetterdatei fehlt oder ist fehlerhaft, bitte erst Wetterdaten neu laden!!")
                exit()
        return data

def storeWeatherData(wetterfile, data, now):
    try:
        out_file = open(wetterfile, "w")
        format = "%Y-%m-%d %H:%M:%S"
        data.update({'messageCreated': datetime.strftime(now, format)})
        json.dump(data, out_file, indent = 6)
        out_file.close()
    except:
        print("ERROR: Die Weterdatei " + wetterfile + " konnte NICHT geschrieben werden!")
        exit(0)
    return()

def loadPVReservierung(file):
        reservierungdata = None
        try:
            with open(file) as json_file:
                reservierungdata = json.load(json_file)
        except:
                print(file , " fehlt, bitte erzeugen oder Option abschalten !!")
                exit()
        return reservierungdata

def getVarConf(block, var, Type):
        # Variablen aus config lesen und auf Zahlen prüfen
        try:
            if(Type == 'eval'):
                error_type = "als Zahl "
                return_var = eval(config[block][var])
            else:
                error_type = ""
                return_var = str(config[block][var])
        except:
            print("ERROR: die Variable [" + block + "][" + var + "] wurde NICHT " + error_type + "definiert!")
            exit(0)
        return return_var


