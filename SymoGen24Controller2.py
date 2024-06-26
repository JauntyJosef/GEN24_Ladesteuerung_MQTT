from datetime import datetime, timedelta
import pytz
import requests
import SymoGen24Connector
import mqtt_functions
import sys
from ping3 import ping
from sys import argv
from functions import loadConfig, loadWeatherData, loadPVReservierung, getVarConf, save_SQLite

def getPrognose(Stunde):
        if data['result']['watts'].get(Stunde):
            data_fun = data['result']['watts'][Stunde]
            # Wenn Reservierung eingeschaltet und Reservierungswert vorhanden von Prognose abziehen.
            if ( PV_Reservierung_steuern == 1 and reservierungdata.get(Stunde)):
                data_fun = data['result']['watts'][Stunde] - reservierungdata[Stunde]
                # Minuswerte verhindern
                if ( data_fun< 0): data_fun = 0
            getPrognose = data_fun
        else:
            getPrognose = 0
        return getPrognose

def getLadewertinGrenzen(Ladewert):
        # aktuellerLadewert zwischen 0 und MaxLadung halten
        if Ladewert < 0: Ladewert = 0
        if (Ladewert > MaxLadung): Ladewert = MaxLadung

        return Ladewert

def getRestTagesPrognoseUeberschuss():

        global BatSparFaktor, DEBUG_Ausgabe
        # alle Prognosewerte zwischen aktueller Stunde und 22:00 lesen
        format_Tag = "%Y-%m-%d"
        # aktuelle Stunde und aktuelle Minute
        Akt_Std = int(datetime.strftime(now, "%H"))
        Akt_Minute = int(datetime.strftime(now, "%M"))

        # Gesamte Tagesprognose, Tagesüberschuß aus Prognose ermitteln
        # Schleife laeft von Grundlast nach oben, bis der Prognoseueberschuss die aktuelle Batteriekapazität erreicht
        i = Akt_Std
        Pro_Ertrag_Tag = 0
        Grundlast_Sum = 0
        Prognose_array = list()
        groestePrognose = 0
        Stunden_sum = 0.0001
        Zwangs_Ueberschuss = 0
        DEBUG_Ausgabe += "\nDEBUG *************** Berechnung Abzugswert: \n"

        # in Schleife Prognosewerte bis BattVollUm durchlaufen
        while i < BattVollUm:
            Std = datetime.strftime(now, format_Tag)+" "+ str('%0.2d' %(i)) +":00:00"
            Prognose = getPrognose(Std)
            if groestePrognose < Prognose:
                groestePrognose = Prognose
            Grundlast_fun = Grundlast
            Einspeisegrenze_fun = Einspeisegrenze
            Stunden_fun = 1

            # wenn nicht zur vollen Stunde, Wert anteilsmaessig
            Grundlast_fun = Grundlast
            if i == Akt_Std:
                Prognose = (Prognose / 60 * (60 - Akt_Minute))
                Grundlast_fun = int((Grundlast / 60 * (60 - Akt_Minute)))
                Einspeisegrenze_fun = int((Einspeisegrenze / 60 * (60 - Akt_Minute)))
                Stunden_fun = (60-Akt_Minute)/60

            Prognose_array.append(Prognose)
            Pro_Ertrag_Tag += Prognose

            # Alles über Einspeisegrenze bzw WR_Kapazitaet von BattKapaWatt_akt abziehen,
            # da dies nicht für die Prognoseberechnung zur Verfügung steht.
            Zwangs_Ueberschuss_fun = (Prognose - Einspeisegrenze_fun - Grundlast_fun)
            if ( Prognose - WR_Kapazitaet > Zwangs_Ueberschuss_fun ): Zwangs_Ueberschuss_fun = Prognose - WR_Kapazitaet
            if ( Zwangs_Ueberschuss_fun > 0): Zwangs_Ueberschuss += Zwangs_Ueberschuss_fun

            Stunden_sum += Stunden_fun

            DEBUG_Ausgabe += "DEBUG ##Schleife## Stunden_sum: " + str(round(Stunden_sum, 3)) + ", Prognose: " + str(round(Prognose,2)) + ", Pro_Ertrag_Tag: " + str(round(Pro_Ertrag_Tag,2)) + "\n"
            Grundlast_Sum += Grundlast_fun

            i += 1

        BattKapaWatt_akt_fun = BattKapaWatt_akt - Zwangs_Ueberschuss
        if Stunden_sum < 1: Stunden_sum = 1
        AbzugsWatt = int((Pro_Ertrag_Tag - BattKapaWatt_akt_fun) / Stunden_sum)
        DEBUG_Ausgabe += "DEBUG #### AbzugsWatt incl. MaxLadung Überschuss: " + str(round(AbzugsWatt, 2)) + "\n"

        # hier noch die Ladewerte über MaxLadung ermitteln und Überschuss von AbzugsWatt abziehen
        # damit wird bei niedrigen Prognosen mehr geladen, da bei hohen nicht über MaxLadung geladen werden kann
        Pro_Uberschuss = 0
        Schleifenzaehler = 0
        for Prognose_einzel in Prognose_array:
            if (Prognose_einzel - AbzugsWatt > MaxLadung): 
                Pro_Uberschuss += Prognose_einzel - AbzugsWatt - MaxLadung
                Schleifenzaehler += 1
        if (Pro_Uberschuss > 0 and Schleifenzaehler > 0):
            AbzugsWatt = int(AbzugsWatt - Pro_Uberschuss / Schleifenzaehler)

        if (AbzugsWatt < 0):
            AbzugsWatt = 0

        Pro_Uebersch_Tag = BattKapaWatt_akt_fun
        DEBUG_Ausgabe += "DEBUG ##Ergebnis## AbzugsWatt: " + str(round(AbzugsWatt, 2)) + ",  Pro_Uebersch_Tag: " + str(round(Pro_Uebersch_Tag, 2)) + ", Stunden_sum: "  + str(round(Stunden_sum, 2)) + "\n"

        return int(Pro_Uebersch_Tag), int(Pro_Ertrag_Tag), AbzugsWatt, Grundlast_Sum, groestePrognose

def getAktuellenLadewert( AbzugWatt, aktuelleEinspeisung, aktuellePVProduktion ):

        global DEBUG_Ausgabe
        format_Tag = "%Y-%m-%d"
        Spreizung = 1
        Akt_Std = int(datetime.strftime(now, "%H"))
        Akt_Minute = int(datetime.strftime(now, "%M"))
        Pro_Akt = 0
        i = Akt_Std - Spreizung
        loop = 0
        while i <= Akt_Std + Spreizung:
            Std = datetime.strftime(now, format_Tag)+" "+ str('%0.2d' %(i)) +":00:00"
            Prognose = getPrognose(Std)
            Pro_Akt_fun = Prognose
            DEBUG_Ausgabe += "\nDEBUG *************** Ladewertmittel LOOP: " + str(loop)
            if loop == 0:
                Pro_Akt_fun = Prognose * (60 - Akt_Minute) / 60
                DEBUG_Ausgabe += "\nDEBUG ########### Pro_Akt_fun: " + str(round(Pro_Akt_fun,2)) + " REST_Akt_Minute: " + str(round(((60 - Akt_Minute) / 60),3))
            if loop == Spreizung * 2:
                Pro_Akt_fun = Prognose * (Akt_Minute) / 60
                DEBUG_Ausgabe += "\nDEBUG ########### Pro_Akt_fun: " + str(round(Pro_Akt_fun,2)) + " Akt_Minute: " + str(round(((Akt_Minute) / 60),3))
            Pro_Akt += Pro_Akt_fun
            DEBUG_Ausgabe += "\nDEBUG  " + str(Std) + " Pro_Akt_fun: " + str(round(Pro_Akt_fun,2)) + " Prognose_gesamt: " + str(round(Pro_Akt,2)) + "\n"
            loop += 1
            i += 1
        Pro_Akt = int(Pro_Akt / Spreizung / 2 )

        # Nun den Aktuellen Ladewert rechnen 
        # Batterieladewert mit allen Einfluessen aus der Prognose rechnen
        aktuellerLadewert = int((Pro_Akt - AbzugWatt) * BatSparFaktor)
        aktuellerLadewert = getLadewertinGrenzen(aktuellerLadewert)

        LadewertGrund = "Prognoseberechnung / BatSparFaktor"

        DEBUG_Ausgabe += "\nDEBUG " + datetime.strftime(now, "%D %H:%M") + " Aktuelle Prognose: " + str(Pro_Akt) + " BatSparFaktor: " + str(BatSparFaktor) + " aktueller Ladewert: " + str(aktuellerLadewert)
        DEBUG_Ausgabe += ", Batteriekapazität: " + str(BattKapaWatt_akt) + ", Abzug: " + str(PrognoseAbzugswert)

        ### Prognose ENDE


        ### Einspeisegrenze ANFANG

        # Hinweis: aktuelleBatteriePower ist beim Laden der Batterie minus
        # Wenn Einspeisung über Einspeisegrenze, dann könnte WR schon abregeln, desshalb WRSchreibGrenze_nachOben addieren
        # Durch Trägheit des WR wird vereinzelt die Einspeisung durch gleichzeitigen Netzbezug größer als die Produktion, dann nicht anwenden
        if (aktuelleEinspeisung - aktuelleBatteriePower > Einspeisegrenze) and aktuelleEinspeisung < aktuellePVProduktion:
            if (aktuelleEinspeisung - aktuelleBatteriePower - alterLadewert > Einspeisegrenze):
                EinspeisegrenzUeberschuss = int(aktuelleEinspeisung + alterLadewert - Einspeisegrenze + (WRSchreibGrenze_nachOben + 5))
            else:
                EinspeisegrenzUeberschuss = int(aktuelleEinspeisung + alterLadewert - Einspeisegrenze)

            # Damit durch die Pufferaddition nicht die maximale PV_Leistung überschritten wird
            if EinspeisegrenzUeberschuss > PV_Leistung_Watt - Einspeisegrenze:
                EinspeisegrenzUeberschuss = PV_Leistung_Watt - Einspeisegrenze

            EinspeisegrenzUeberschuss = getLadewertinGrenzen(EinspeisegrenzUeberschuss)

            if EinspeisegrenzUeberschuss > aktuellerLadewert and alterLadewert <= (MaxLadung + 100):
                DEBUG_Ausgabe += "\nDEBUG EinspeisegrenzUeberschuss: " + str(EinspeisegrenzUeberschuss) + " aktuellerLadewert: " + str(aktuellerLadewert) + " alterLadewert: " + str(alterLadewert)
                aktuellerLadewert = int(EinspeisegrenzUeberschuss)
                LadewertGrund = "PV_Leistungsüberschuss > Einspeisegrenze"

        aktuellerLadewert = getLadewertinGrenzen(aktuellerLadewert)

        ### Einspeisegrenze ENDE

        ### AC_Kapazitaet WR ANFANG

        # Wenn  PV-Produktion > WR_Kapazitaet (AC)
        if aktuellePVProduktion > WR_Kapazitaet:
            kapazitaetsueberschuss = int(aktuellePVProduktion - WR_Kapazitaet )
            #if (kapazitaetsueberschuss > alterLadewert * 1.1):
            if (kapazitaetsueberschuss > alterLadewert):
                if (kapazitaetsueberschuss < alterLadewert + WRSchreibGrenze_nachOben):
                    kapazitaetsueberschuss = alterLadewert + WRSchreibGrenze_nachOben + 10
                    # Damit der kapazitaetsueberschuss durch die Addition der WRSchreibGrenze_nachOben nicht grösser als die PV_Leistung_Watt wird.
                    if kapazitaetsueberschuss > PV_Leistung_Watt - WR_Kapazitaet:
                        kapazitaetsueberschuss = PV_Leistung_Watt - WR_Kapazitaet
                aktuellerLadewert = kapazitaetsueberschuss
                LadewertGrund = "PV-Produktion > AC_Kapazitaet WR"

        aktuellerLadewert = getLadewertinGrenzen(aktuellerLadewert)

        ### AC_Kapazitaet WR ENDE


        return  aktuellerLadewert, Pro_Akt, LadewertGrund

def setLadewert(fun_Ladewert):
        fun_Ladewert = getLadewertinGrenzen(fun_Ladewert)

        newPercent = (int(fun_Ladewert/BattganzeLadeKapazWatt*10000))
        if newPercent < LadungAus:
            newPercent = LadungAus

        # Schaltvezögerung
        # mit altem Ladewert vergleichen
        diffLadewert_nachOben = int(fun_Ladewert - oldPercent*BattganzeLadeKapazWatt/10000)
        diffLadewert_nachUnten = int((oldPercent*BattganzeLadeKapazWatt/10000) - fun_Ladewert)

        # Wenn die Differenz in hundertstel Prozent kleiner als die Schreibgrenze nix schreiben
        newPercent_schreiben = 0
        if ( diffLadewert_nachOben > WRSchreibGrenze_nachOben ):
            newPercent_schreiben = 1
        if ( diffLadewert_nachUnten > WRSchreibGrenze_nachUnten ):
            newPercent_schreiben = 1

        # Wenn MaxLadung erstmals erreicht ist immer schreiben
        if (fun_Ladewert == MaxLadung) and (abs(diffLadewert_nachOben) > 3):
            newPercent_schreiben = 1

        return(newPercent, newPercent_schreiben)

def getPrognoseMorgen():
    i = 0
    Prognose_Summe = 0
    while i < 24:
        Std_morgen = datetime.strftime(now + timedelta(days=1), "%Y-%m-%d")+" "+ str('%0.2d' %(i)) +":00:00"
        Prognose_Summe += getPrognose(Std_morgen)
        i  += 1
    return(Prognose_Summe)
    

if __name__ == '__main__':
        config = loadConfig('config.ini')
        now = datetime.now()
        format = "%Y-%m-%d %H:%M:%S"

        mqtt_status = getVarConf('MQTT', "mqtt", 'eval')
        host_ip = getVarConf('gen24','hostNameOrIp', 'str')
        host_port = getVarConf('gen24','port', 'str')
        print_level = getVarConf('Ladeberechnung','print_level','eval')

        try:
            print("\n")          
            print("************* BEGINN: ", datetime.now(),"************* ") 
        except Exception as e:
            print()
            print("Fehler in den Printbefehlen, Ausgabe nicht möglich!")
            print("Fehlermeldung:", e)
            print()

        print("################# M Q T T #################")
        if  mqtt_status == 1:
            print("MQTT ist aktiviert.")
            # Prüfen, ob Skript ausgeführt werden soll
            try:
                print("\n# Prüfe ob Steuerung aktiviert werden soll:\n")
                maintopic = config.get('MQTT', 'maintopic')
                control_topic = config.get('MQTT', 'control_topic')
                steuerung = mqtt_functions.subscribe_to_topic(maintopic + "/" + control_topic)
                if steuerung == None:
                    print("An- und ausschalten der Steuerung per MQTT nicht möglich. Entsprechendes Topic ist nicht vorhanden.")
                elif steuerung == "1":
                    print("Die automatische Steuerung ist an ... Programm wird fortgesetzt")
                elif steuerung == "0":
                    print("Die automatische Steuerung ist aus ... Programm wird beendet.")
                    print()
                    print("************* ENDE: ", datetime.now(),"************* \n")   
                    sys.exit(0)
                else:
                    print("Kein gültiger Wert empfangen. Programm wird fortgesetzt.")
            except Exception as e:
                print("!!!! ACHTUNG FEHLER !!!! Bitte Fehlermeldung beachten!")
                print("Fehlermeldung:", e)
                print()
                steurungsdata = loadPVReservierung("./Steuerung.json")
                # Manuellen Entladewert lesen
                steuerung = steurungsdata.get('Steuerung')
                try:
                    print("\n# Prüfe ob Steuerung aktiviert werden soll:\n")
                    if steuerung == None:
                        print("Keine Daten vorhanden.")
                    elif steuerung == "1":
                        print("Die automatische Steuerung ist an ... Programm wird fortgesetzt")
                    elif steuerung == "0":
                        print("Die automatische Steuerung ist aus ... Programm wird beendet.")
                        print()
                        print("************* ENDE: ", datetime.now(),"************* \n")   
                        sys.exit(0)
                    else:
                        print("Kein gültiger Wert empfangen. Programm wird fortgesetzt.")
                except Exception as e:
                    print("!!!! ACHTUNG FEHLER !!!! Bitte Fehlermeldung beachten!")
                    print("Fehlermeldung:", e)
                    print()

            # Lade- Entladerate über MQTT holen
            try:        
                print("\n# Lade- und Entladerate empfangen und in JSON schreiben\n") 
                mqtt_functions.lesen()
            except Exception as e:
                print("!!!! ACHTUNG FEHLER !!!! Bitte Fehlermeldung beachten!")
                print("Fehlermeldung:", e)
                print()

        if  mqtt_status == 0:
            print("MQTT ist deakiviert.")
            # Steuerungsfile lesen
            #SteuerungFile = getVarConf('Entladung','Akku_EntladeSteuerungsFile','str')
            steurungsdata = loadPVReservierung("./Steuerung.json")
            # Manuellen Entladewert lesen
            steuerung = steurungsdata.get('Steuerung')
            try:
                print("\n# Prüfe ob Steuerung aktiviert werden soll:\n")
                if steuerung == None:
                    print("Keine Daten vorhanden.")
                elif steuerung == "1":
                    print("Die automatische Steuerung ist an ... Programm wird fortgesetzt")
                elif steuerung == "0":
                    print("Die automatische Steuerung ist aus ... Programm wird beendet.")
                    print()
                    print("************* ENDE: ", datetime.now(),"************* \n")   
                    sys.exit(0)
                else:
                    print("Kein gültiger Wert empfangen. Programm wird fortgesetzt.")
            except Exception as e:
                print("!!!! ACHTUNG FEHLER !!!! Bitte Fehlermeldung beachten!")
                print("Fehlermeldung:", e)
                print()


        if ping(host_ip):
            # Nur ausführen, wenn WR erreichbar
            gen24 = None
            auto = False
            try:            
                    newPercent = None
                    DEBUG_Ausgabe= "\nDEBUG <<<<<< E I N >>>>>>>\n"
                    ###############################
    
                    weatherfile = getVarConf('env','filePathWeatherData','str')
                    data = loadWeatherData(weatherfile)

                    gen24 = SymoGen24Connector.SymoGen24(host_ip, host_port, auto)

                    if gen24.read_data('Battery_Status') == 1:
                        print(datetime.now())
                        print("Batterie ist Offline keine Steuerung möglich!!! ")
                        print()
                        exit()
    
                    # Benoetigte Variablen aus config.ini definieren und auf Zahlen prüfen
                    print_level = getVarConf('Ladeberechnung','print_level','eval')
                    BattVollUm = getVarConf('Ladeberechnung','BattVollUm','eval')
                    BatSparFaktor = getVarConf('Ladeberechnung','BatSparFaktor','eval')
                    MaxLadung = getVarConf('Ladeberechnung','MaxLadung','eval')
                    LadungAus = getVarConf('Ladeberechnung','LadungAus','eval')
                    Akkuschonung = getVarConf('Ladeberechnung','Akkuschonung','eval')
                    Einspeisegrenze = getVarConf('Ladeberechnung','Einspeisegrenze','eval')
                    WR_Kapazitaet = getVarConf('Ladeberechnung','WR_Kapazitaet','eval')
                    PV_Leistung_Watt = getVarConf('Ladeberechnung','PV_Leistung_Watt','eval')
                    Grundlast = getVarConf('Ladeberechnung','Grundlast','eval')
                    MindBattLad = getVarConf('Ladeberechnung','MindBattLad','eval')
                    GrenzwertGroestePrognose = getVarConf('Ladeberechnung','GrenzwertGroestePrognose','eval')
                    WRSchreibGrenze_nachOben = getVarConf('Ladeberechnung','WRSchreibGrenze_nachOben','eval')
                    WRSchreibGrenze_nachUnten = getVarConf('Ladeberechnung','WRSchreibGrenze_nachUnten','eval')
                    FesteLadeleistung = getVarConf('Ladeberechnung','FesteLadeleistung','eval')
                    Fallback_on = getVarConf('Fallback','Fallback_on','eval')
                    Cronjob_Minutenabstand = getVarConf('Fallback','Cronjob_Minutenabstand','eval')
                    Fallback_Zeitabstand_Std = getVarConf('Fallback','Fallback_Zeitabstand_Std','eval')
                    Push_Message_EIN = getVarConf('messaging','Push_Message_EIN','eval')
                    PV_Reservierung_steuern = getVarConf('Reservierung','PV_Reservierung_steuern','eval')
                    Batterieentlandung_steuern = getVarConf('Entladung','Batterieentlandung_steuern','eval')
                    WREntladeSchreibGrenze_Watt = getVarConf('Entladung','WREntladeSchreibGrenze_Watt','eval')
                    EntladeGrenze_steuern = getVarConf('Entladung','EntladeGrenze_steuern','eval')

                    # um Divison durch Null zu verhindern kleinsten Wert setzen
                    if BatSparFaktor < 0.1:
                        BatSparFaktor = 0.1
                                       
                    # Bei Akkuschonung BattVollUm eine Stunde vor verlegen
                    if Akkuschonung == 1:
                        BattVollUm = BattVollUm - 1

                    # Grundlast je Wochentag, wenn Grundlast == 0
                    if (Grundlast == 0):
                        try:
                            Grundlast_WoT = getVarConf('Ladeberechnung','Grundlast_WoT','str')
                            Grundlast_WoT_Array = Grundlast_WoT.split(',')
                            Grundlast = eval(Grundlast_WoT_Array[datetime.today().weekday()])
                        except:
                            print("ERROR: Grundlast für den Wochentag konnte nicht gelesen werden, Grundlast = 0 !!")
                            Grundlast = 0


                    # Benoetigte Variablen vom GEN24 lesen und definieren
                    BattganzeLadeKapazWatt = (gen24.read_data('BatteryChargeRate')) + 1  # +1 damit keine Divison duch Null entstehen kann
                    BattganzeKapazWatt = (gen24.read_data('Battery_capa')) + 1  # +1 damit keine Divison duch Null entstehen kann
                    BattStatusProz = gen24.read_data('Battery_SoC')/100
                    BattKapaWatt_akt = int((1 - BattStatusProz/100) * BattganzeKapazWatt)
                    aktuelleEinspeisung = int(gen24.get_meter_power() * -1)
                    aktuellePVProduktion = int(gen24.get_mppt_power())
                    aktuelleBatteriePower = int(gen24.get_batterie_power())
                    BatteryMaxDischargePercent = int(gen24.read_data('BatteryMaxDischargePercent')/100) 
                    GesamtverbrauchHaus = aktuellePVProduktion - aktuelleEinspeisung + aktuelleBatteriePower

                    # Reservierungsdatei lesen, wenn Reservierung eingeschaltet
                    if  PV_Reservierung_steuern == 1:
                        Reservierungsdatei = getVarConf('Reservierung','PV_ReservieungsDatei','str')
                        reservierungdata = loadPVReservierung(Reservierungsdatei)

                    # 0 = nicht auf WR schreiben, 1 = schon auf WR schreiben
                    newPercent_schreiben = 0
                    oldPercent = gen24.read_data('BatteryMaxChargePercent')
                    alterLadewert = int(oldPercent*BattganzeLadeKapazWatt/10000)
    
                    format_aktStd = "%Y-%m-%d %H:00:00"
    
    
                    #######################################
                    ## Ab hier geht die Berechnung los
                    #######################################
    
                    TagesPrognoseUeberschuss = 0
                    TagesPrognoseGesamt = 0
                    aktuellerLadewert = 0
                    PrognoseAbzugswert = 0
                    Grundlast_Summe = 0
                    aktuelleVorhersage = 0
                    LadewertGrund = ""

                    # WRSchreibGrenze_nachUnten ab 90% Batteriestand prozentual erhöhen (ersetzen von BatterieVoll!!)
                    if ( BattStatusProz > 90 ):
                        WRSchreibGrenze_nachUnten = int(WRSchreibGrenze_nachUnten * (1 + ( BattStatusProz - 90 ) / 5))
                        DEBUG_Ausgabe += "DEBUG ## Batt >90% ## WRSchreibGrenze_nachUnten: " + str(WRSchreibGrenze_nachUnten) +"\n"
                        WRSchreibGrenze_nachOben = int(WRSchreibGrenze_nachOben * (1 + ( BattStatusProz - 90 ) / 5))
                        DEBUG_Ausgabe += "DEBUG ## Batt >90% ## WRSchreibGrenze_nachOben: " + str(WRSchreibGrenze_nachOben) +"\n"

                    # Prognoseberechnung mit Funktion getRestTagesPrognoseUeberschuss
                    PrognoseUNDUeberschuss = getRestTagesPrognoseUeberschuss()
                    TagesPrognoseUeberschuss = PrognoseUNDUeberschuss[0]
                    TagesPrognoseGesamt = PrognoseUNDUeberschuss[1]
                    PrognoseAbzugswert = PrognoseUNDUeberschuss[2]
                    Grundlast_Summe = PrognoseUNDUeberschuss[3]
                    GroestePrognose = PrognoseUNDUeberschuss[4]

                    # Nun der aktuellen Ladewert mit dem ermittelten PrognoseAbzugswert bestimmen
                    AktuellenLadewert_Array = getAktuellenLadewert( PrognoseAbzugswert, aktuelleEinspeisung, aktuellePVProduktion )
                    aktuellerLadewert = AktuellenLadewert_Array[0]
                    aktuelleVorhersage = AktuellenLadewert_Array[1]
                    LadewertGrund = AktuellenLadewert_Array[2]

                    # DEBUG_Ausgabe der Ladewertermittlung 
                    DEBUG_Ausgabe += "\nDEBUG TagesPrognoseUeberschuss: " + str(TagesPrognoseUeberschuss) + ", Grundlast: " + str(Grundlast)
                    DEBUG_Ausgabe += ", aktuellerLadewert: " + str(aktuellerLadewert) + "\n"


                    # Wenn über die PV-Planung manuelle Ladung angewählt wurde
                    MaxladungDurchPV_Planung = ""
                    if (PV_Reservierung_steuern == 1) and (reservierungdata.get('ManuelleSteuerung')):
                        FesteLadeleistung = MaxLadung * reservierungdata.get('ManuelleSteuerung')
                        if (reservierungdata.get('ManuelleSteuerung') != 0):
                            MaxladungDurchPV_Planung = "Manuelle Ladesteuerung in PV-Planung ausgewählt."

                    # Wenn die Variable "FesteLadeleistung" größer "0" ist, wird der Wert fest als Ladeleistung in Watt geschrieben einstellbare Wattzahl
                    if FesteLadeleistung > 0:
                        DATA = setLadewert(FesteLadeleistung)
                        aktuellerLadewert = FesteLadeleistung
                        newPercent = DATA[0]
                        if newPercent == oldPercent:
                            newPercent_schreiben = 0
                        else:
                            newPercent_schreiben = 1
                        if MaxladungDurchPV_Planung == "":
                            LadewertGrund = "FesteLadeleistung"
                        else:
                            LadewertGrund = MaxladungDurchPV_Planung
    
                    # Hier Volle Ladung, wenn Stunde aus BattVollUm erreicht ist!
                    elif (int(datetime.strftime(now, "%H")) >= int(BattVollUm)):
                         aktuellerLadewert = MaxLadung
                         DATA = setLadewert(aktuellerLadewert)
                         newPercent = DATA[0]
                         newPercent_schreiben = DATA[1]
                         LadewertGrund = "Stunde aus BattVollUm erreicht!!"
        
                    else:

                        # Schaltverzögerung für MindBattLad
                        if (alterLadewert+2 > MaxLadung):
                            MindBattLad = MindBattLad +5

                        if ((BattStatusProz < MindBattLad)):
                            # volle Ladung ;-)
                            aktuellerLadewert = MaxLadung
                            DATA = setLadewert(MaxLadung)
                            newPercent = DATA[0]
                            newPercent_schreiben = DATA[1]
                            LadewertGrund = "BattStatusProz < MindBattLad"
    
                        else:
    
                            if (TagesPrognoseGesamt > Grundlast) and ((TagesPrognoseGesamt - Grundlast_Summe) < BattKapaWatt_akt):
                                # Auch hier die Schaltverzögerung anbringen und dann MaxLadung, also immer nach oben.
                                if BattKapaWatt_akt + Grundlast_Summe - TagesPrognoseGesamt < WRSchreibGrenze_nachOben:
                                    # Nach Prognoseberechnung darf es trotzdem nach oben gehen aber nicht von MaxLadung nach unten !
                                    WRSchreibGrenze_nachUnten = 100000
                                    DATA = setLadewert(aktuellerLadewert)
                                    newPercent = DATA[0]
                                    newPercent_schreiben = DATA[1]
                                    # Nur wenn newPercent_schreiben = 0 dann LadewertGrund mit Hinweis übreschreiben
                                    if newPercent_schreiben == 0:
                                        newPercent = oldPercent
                                        LadewertGrund = "TagesPrognoseGesamt - Grundlast_Summe < BattKapaWatt_akt (Unterschied weniger als Schreibgrenze)"
                                else:
                                    # volle Ladung ;-)
                                    aktuellerLadewert = MaxLadung
                                    DATA = setLadewert(MaxLadung)
                                    newPercent = DATA[0]
                                    newPercent_schreiben = DATA[1]
                                    LadewertGrund = "TagesPrognoseGesamt - Grundlast_Summe < BattKapaWatt_akt"
    
                            # PrognoseAbzugswert - 100 um Schaltverzögerung wieder nach unten zu erreichen
                            elif (TagesPrognoseUeberschuss < BattKapaWatt_akt) and (PrognoseAbzugswert - 100 <= Grundlast):
                                # Auch hier die Schaltverzögerung anbringen und dann MaxLadung, also immer nach oben.
                                if BattKapaWatt_akt - TagesPrognoseUeberschuss < WRSchreibGrenze_nachOben:
                                    # Nach Prognoseberechnung darf es trotzdem nach oben gehen aber nicht von MaxLadung nach unten !
                                    WRSchreibGrenze_nachUnten = 100000
                                    DATA = setLadewert(aktuellerLadewert)
                                    newPercent = DATA[0]
                                    newPercent_schreiben = DATA[1]
                                    # Nur wenn newPercent_schreiben = 0 dann LadewertGrund mit Hinweis übreschreiben
                                    if newPercent_schreiben == 0:
                                        LadewertGrund = "PrognoseAbzugswert nahe Grundlast (Unterschied weniger als Schreibgrenze)"
                                else:
                                    # volle Ladung ;-)
                                    aktuellerLadewert = MaxLadung
                                    DATA = setLadewert(aktuellerLadewert)
                                    newPercent = DATA[0]
                                    newPercent_schreiben = DATA[1]
                                    LadewertGrund = "PrognoseAbzugswert kleiner Grundlast und Schreibgrenze"

                            else: 
                                DATA = setLadewert(aktuellerLadewert)
                                newPercent = DATA[0]
                                newPercent_schreiben = DATA[1]

                        # Wenn größter Prognosewert je Stunde ist kleiner als GrenzwertGroestePrognose volle Ladung
                        if GrenzwertGroestePrognose > GroestePrognose:
                            aktuellerLadewert = MaxLadung
                            DATA = setLadewert(aktuellerLadewert)
                            newPercent = DATA[0]
                            newPercent_schreiben = DATA[1]
                            LadewertGrund = "Größter Prognosewert " + str(GroestePrognose) + " ist kleiner als GrenzwertGroestePrognose " + str(GrenzwertGroestePrognose)

                    # Wenn Akkuschonung = 1 ab 80% Batterieladung mit Ladewert runter fahren
                    if Akkuschonung == 1:
                        Ladefaktor = 1
                        BattStatusProz_Grenze = 100
                        if BattStatusProz > 80:
                            Ladefaktor = 0.2
                            AkkuSchonGrund = '80%, Ladewert = 0.2C'
                            BattStatusProz_Grenze = 80
                        if BattStatusProz > 90:
                            Ladefaktor = 0.1
                            AkkuSchonGrund = '90%, Ladewert = 0.1C'
                            BattStatusProz_Grenze = 90
                        # Bei Akkuschonung Schaltverzögerung (hysterese) einbauen, wenn Ladewert ist bereits der Akkuschonwert (+/- 3%) BattStatusProz_Grenze 5% runter
                        AkkuschonungLadewert = (BattganzeKapazWatt * Ladefaktor)
                        if ( abs(AkkuschonungLadewert - alterLadewert) < 3 ):
                            BattStatusProz_Grenze = BattStatusProz_Grenze * 0.95

                        if BattStatusProz > BattStatusProz_Grenze:
                            DEBUG_Ausgabe += "\nDEBUG <<<<<< Meldungen von Akkuschonung >>>>>>> "
                            DEBUG_Ausgabe += "\nDEBUG AkkuschonungLadewert-alterLadewert: " + str(abs(AkkuschonungLadewert - alterLadewert))
                            DEBUG_Ausgabe += "\nDEBUG BattStatusProz_Grenze: " + str(BattStatusProz_Grenze)
                            DEBUG_Ausgabe += "\nDEBUG aktuelleVorhersage - (Grundlast /2) > AkkuschonungLadewert? " + str(aktuelleVorhersage - (Grundlast /2))
                            DEBUG_Ausgabe += "\nDEBUG AkkuschonungLadewert: " + str(AkkuschonungLadewert) + "\n"
                            DEBUG_Ausgabe += "DEBUG aktuellerLadewert: " + str(aktuellerLadewert) + "\n"
                            # Um des setzen der Akkuschonung zu verhindern, wenn zu wenig PV Energie kommt oder der Akku wieder entladen wird nur bei entspechender Vorhersage anwenden
                            if (AkkuschonungLadewert < aktuellerLadewert or AkkuschonungLadewert < alterLadewert + 10) and aktuelleVorhersage - (Grundlast /2) > AkkuschonungLadewert:
                                aktuellerLadewert = AkkuschonungLadewert
                                WRSchreibGrenze_nachUnten = aktuellerLadewert / 5
                                WRSchreibGrenze_nachOben = aktuellerLadewert / 5
                                DATA = setLadewert(aktuellerLadewert)
                                newPercent = DATA[0]
                                newPercent_schreiben = DATA[1]
                                LadewertGrund = "Akkuschonung: Ladestand > " + AkkuSchonGrund

                    # Wenn die aktuellePVProduktion < 10 Watt ist, nicht schreiben, 
                    # um 0:00Uhr wird sonst immer Ladewert 0 geschrieben!
                    if aktuellePVProduktion < 10:
                        newPercent_schreiben = 0
                        LadewertGrund = "Nicht schreiben, da PVProduktion < 10 Watt!"

                    # Auf ganze Watt runden
                    aktuellerLadewert = int(aktuellerLadewert)

                    if print_level >= 1:
                        try:
                            #print("************* BEGINN: ", datetime.now(),"************* ")
                            print("\n######### L A D E S T E U E R U N G #########\n")
                            print("MQTT Status:                ", mqtt_status)
                            print("aktuellePrognose:           ", aktuelleVorhersage)
                            print("RestTagesPrognose:          ", TagesPrognoseGesamt)
                            print("PrognoseAbzugswert/Stunde:  ", PrognoseAbzugswert)
                            print("Grundlast_Summe für Tag:    ", Grundlast_Summe)
                            print("aktuellePVProduktion/Watt:  ", aktuellePVProduktion)
                            print("aktuelleEinspeisung/Watt:   ", aktuelleEinspeisung)
                            print("aktuelleBatteriePower/Watt: ", aktuelleBatteriePower)
                            print("GesamtverbrauchHaus/Watt:   ", GesamtverbrauchHaus)
                            print("aktuelleBattKapazität/Watt: ", BattKapaWatt_akt)
                            print("Batteriestatus in Prozent:  ", BattStatusProz,"%")
                            print("LadewertGrund: ", LadewertGrund)
                            print("Bisheriger Ladewert/Watt:   ", alterLadewert)
                            print("Bisheriger Ladewert/Prozent:", oldPercent/100,"%")
                            print("Neuer Ladewert/Watt:        ", aktuellerLadewert)
                            print("Neuer Ladewert/Prozent:     ", newPercent/100,"%")
                            print("newPercent_schreiben:       ", newPercent_schreiben)
                            # dataBatteryStats = gen24.read_section('StorageDevice')
                            # print(f'Battery Stats: {dataBatteryStats}') 
                            print()
                        except Exception as e:
                            print()
                            print("Fehler in den Printbefehlen, Ausgabe nicht möglich!")
                            print("Fehlermeldung:", e)
                            print()


                    DEBUG_Ausgabe+="\nDEBUG BattVollUm:                 " + str(BattVollUm) + "Uhr"
                    DEBUG_Ausgabe+="\nDEBUG WRSchreibGrenze_nachUnten:  " + str(WRSchreibGrenze_nachUnten) + "W"
                    DEBUG_Ausgabe+="\nDEBUG WRSchreibGrenze_nachOben:   " + str(WRSchreibGrenze_nachOben) + "W"
                    ### AB HIER SCHARF wenn Argument "schreiben" übergeben

                    bereits_geschrieben = 0
                    Schreib_Ausgabe = ""
                    Push_Schreib_Ausgabe = ""
                    # Neuen Ladewert in Prozent schreiben, wenn newPercent_schreiben == 1
                    if newPercent_schreiben == 1:
                        DEBUG_Ausgabe+="\nDEBUG <<<<<<<< LADEWERTE >>>>>>>>>>>>>"
                        DEBUG_Ausgabe+="\nDEBUG Folgender Ladewert neu zum Schreiben: " + str(newPercent)
                        if len(argv) > 1 and (argv[1] == "schreiben"):
                            valueNew = gen24.write_data('BatteryMaxChargePercent', newPercent)
                            bereits_geschrieben = 1
                            Schreib_Ausgabe = Schreib_Ausgabe + "Am WR geschrieben: " + str(newPercent / 100) + "% = " + str(aktuellerLadewert) + "W\n"
                            Push_Schreib_Ausgabe = Push_Schreib_Ausgabe + Schreib_Ausgabe
                            DEBUG_Ausgabe+="\nDEBUG Meldung bei Ladegrenze schreiben: " + str(valueNew)
                        else:
                            Schreib_Ausgabe = Schreib_Ausgabe + "Es wurde nix geschrieben, da NICHT \"schreiben\" übergeben wurde: \n"
                    else:
                        Schreib_Ausgabe = Schreib_Ausgabe + "Alte und Neue Werte unterscheiden sich weniger als die Schreibgrenzen des WR, NICHTS zu schreiben!!\n"

                    # Ladungsspeichersteuerungsmodus aktivieren wenn nicht aktiv
                    # kann durch Fallback (z.B. nachts) erfordelich sein, ohne dass Änderung an der Ladeleistung nötig ist
                    if gen24.read_data('StorageControlMode') != 3:
                        if len(argv) > 1 and (argv[1] == "schreiben"):
                            DEBUG_Ausgabe += "\nDEBUG StorageControlMode 3 schreiben! "
                            valueNew = gen24.write_data('StorageControlMode', 3 )
                            bereits_geschrieben = 1
                            Schreib_Ausgabe = Schreib_Ausgabe + "StorageControlMode 3 neu geschrieben.\n"
                            Push_Schreib_Ausgabe += "StorageControlMode 3 neu geschrieben.\n"
                            DEBUG_Ausgabe+="\nDEBUG Meldung bei StorageControlMode schreiben: " + str(valueNew)
                        else:
                            Schreib_Ausgabe = Schreib_Ausgabe + "StorageControlMode neu wurde NICHT geschrieben, da NICHT \"schreiben\" übergeben wurde:\n"

                    if print_level >= 1:
                        print(Schreib_Ausgabe)
    
                    ######## E N T L A D E S T E U E R U N G  ab hier wenn eingeschaltet!

                    if  Batterieentlandung_steuern == 1:
                        MaxEntladung = 100

                        DEBUG_Ausgabe+="\nDEBUG <<<<<<<< ENTLADESTEUERUNG >>>>>>>>>>>>>"

                        # EntladeSteuerungFile lesen
                        EntladeSteuerungFile = getVarConf('Entladung','Akku_EntladeSteuerungsFile','str')
                        entladesteurungsdata = loadPVReservierung(EntladeSteuerungFile)
                        # Manuellen Entladewert lesen
                        if (entladesteurungsdata.get('ManuelleEntladesteuerung')):
                            MaxEntladung = entladesteurungsdata['ManuelleEntladesteuerung']['Res_Feld1']
                            DEBUG_Ausgabe+="\nDEBUG MaxEntladung = entladesteurungsdata:" + str(MaxEntladung)

                        aktStd = datetime.strftime(now, "%H:00")

                        # Verbrauchsgrenze Entladung lesen
                        if (entladesteurungsdata.get(aktStd)):
                            VerbrauchsgrenzeEntladung = entladesteurungsdata[aktStd]['Res_Feld1']
                        else:
                            VerbrauchsgrenzeEntladung = 0

                        DEBUG_Ausgabe+="\nDEBUG VerbrauchsgrenzeEntladung aus Spalte 1: " + str(VerbrauchsgrenzeEntladung)
                        # Feste Entladegrenze lesen
                        if (entladesteurungsdata.get(aktStd)):
                            FesteEntladegrenze = entladesteurungsdata[aktStd]['Res_Feld2']
                        else:
                            FesteEntladegrenze = 0

                        DEBUG_Ausgabe+="\nDEBUG FesteEntladegrenze aus Spalte 2: " + str(FesteEntladegrenze)

                        # Wenn folgende Bedingungen wahr, Entladung neu schreiben
                        # Verbrauchsgrenze == 2000 && Feste Grenze == 0 (leer)
                        if (GesamtverbrauchHaus > VerbrauchsgrenzeEntladung and VerbrauchsgrenzeEntladung > 0 and FesteEntladegrenze == 0):
                            Neu_BatteryMaxDischargePercent = int((GesamtverbrauchHaus - VerbrauchsgrenzeEntladung)/BattganzeLadeKapazWatt*100)
                        # Verbrauchsgrenze == 2000 && Feste Grenze == 500 
                        elif (GesamtverbrauchHaus > VerbrauchsgrenzeEntladung and VerbrauchsgrenzeEntladung > 0 and FesteEntladegrenze > 0):
                            Neu_BatteryMaxDischargePercent = int(FesteEntladegrenze/BattganzeLadeKapazWatt*100)
                        # Verbrauchsgrenze == 0 (leer) && Feste Grenze == 500
                        elif (VerbrauchsgrenzeEntladung == 0 and FesteEntladegrenze > 0):
                            Neu_BatteryMaxDischargePercent = int(FesteEntladegrenze/BattganzeLadeKapazWatt*100)
                        else:
                            Neu_BatteryMaxDischargePercent = MaxEntladung

                        DEBUG_Ausgabe+="\nDEBUG Batterieentladegrenze NEU: " + str(Neu_BatteryMaxDischargePercent) + "%"

                        # Entladung_Daempfung, Unterschied muss größer WREntladeSchreibGrenze_Watt sein
                        WREntladeSchreibGrenze_Prozent = int(WREntladeSchreibGrenze_Watt / BattganzeLadeKapazWatt * 100 + 1)
                        if (abs(Neu_BatteryMaxDischargePercent - BatteryMaxDischargePercent) < WREntladeSchreibGrenze_Prozent):
                            Neu_BatteryMaxDischargePercent = BatteryMaxDischargePercent

                        ## Werte zum Überprüfen ausgeben
                        if print_level >= 1:
                            print("######### E N T L A D E S T E U E R U N G #########\n")
                            print("Feste Entladegrenze:       ", entladesteurungsdata['ManuelleEntladesteuerung']['Res_Feld1'], "%")
                            print("Batteriestatus in Prozent: ", BattStatusProz, "%")
                            print("GesamtverbrauchHaus:       ", GesamtverbrauchHaus, "W")
                            print("VerbrauchsgrenzeEntladung: ", VerbrauchsgrenzeEntladung, "W")
                            print("Batterieentladegrenze ALT: ", BatteryMaxDischargePercent, "%")
                            print("Batterieentladegrenze NEU: ", Neu_BatteryMaxDischargePercent, "%")
                            print()

                        Schreib_Ausgabe = ""

                        if (Neu_BatteryMaxDischargePercent != BatteryMaxDischargePercent):
                            if len(argv) > 1 and (argv[1] == "schreiben"):
                                valueNew = gen24.write_data('BatteryMaxDischargePercent', Neu_BatteryMaxDischargePercent * 100)
                                bereits_geschrieben = 1
                                DEBUG_Ausgabe+="\nDEBUG Meldung Entladewert schreiben: " + str(valueNew)
                                Schreib_Ausgabe = Schreib_Ausgabe + "Folgender Wert wurde geschrieben für Batterieentladung: " + str(Neu_BatteryMaxDischargePercent) + "%\n"
                                Push_Schreib_Ausgabe = Push_Schreib_Ausgabe + Schreib_Ausgabe 
                            else:
                                Schreib_Ausgabe = Schreib_Ausgabe + "Für Batterieentladung wurde NICHT " + str(Neu_BatteryMaxDischargePercent) +"% geschrieben, da NICHT \"schreiben\" übergeben wurde: \n"
                        else:
                            Schreib_Ausgabe = Schreib_Ausgabe + "Unterschied Alte und Neue Werte der Batterieentladung kleiner ("+ str(WREntladeSchreibGrenze_Watt) + "W), NICHTS zu schreiben!!\n"

                        if print_level >= 1:
                            print(Schreib_Ausgabe)

                        DEBUG_Ausgabe+="\nDEBUG <<<<<<<< ENDE ENTLADESTEUERUNG >>>>>>>>>>>>>"

                    ######## E N T L A D E B E G R E N Z U N G ab hier wenn eingeschaltet!
                    if  EntladeGrenze_steuern == 1:
                        DEBUG_Ausgabe+="\nDEBUG <<<<<<<< ENTLADEBEGRENZUNG >>>>>>>>>>>>>"

                        MaxEntladung = 100
                        ProgGrenzeMorgen = getVarConf('Entladung','ProgGrenzeMorgen','eval')
                        EntladeGrenze_Min = getVarConf('Entladung','EntladeGrenze_Min','eval')
                        EntladeGrenze_Max = getVarConf('Entladung','EntladeGrenze_Max','eval')
                        PrognoseMorgen = getPrognoseMorgen()/1000
                        Battery_MinRsvPct = int(gen24.read_data('Battery_MinRsvPct')/100)
                        Neu_Battery_MinRsvPct = EntladeGrenze_Min
                        if (PrognoseMorgen < ProgGrenzeMorgen and PrognoseMorgen != 0):
                            Neu_Battery_MinRsvPct = EntladeGrenze_Max
                        if print_level >= 1:
                            print("######### E N T L A D E B E G R E N Z U N G #########\n")
                            print("Prognose Morgen: ", PrognoseMorgen, "KW")
                            print("Batteriereserve: ", Battery_MinRsvPct, "%")
                            print("Neu_Batteriereserve: ", Neu_Battery_MinRsvPct, "%")
                            print()

                        Schreib_Ausgabe = ""

                        if (Neu_Battery_MinRsvPct != Battery_MinRsvPct):
                            if len(argv) > 1 and (argv[1] == "schreiben"):
                                valueNew = gen24.write_data('Battery_MinRsvPct', Neu_Battery_MinRsvPct * 100)
                                bereits_geschrieben = 1
                                DEBUG_Ausgabe+="\nDEBUG Meldung Entladegrenze schreiben: " + str(valueNew)
                                Schreib_Ausgabe = Schreib_Ausgabe + "Folgender Wert wurde geschrieben für Batterieentladebegrenzung: " + str(Neu_Battery_MinRsvPct) + "%\n"
                                Push_Schreib_Ausgabe = Push_Schreib_Ausgabe + Schreib_Ausgabe 
                            else:
                                Schreib_Ausgabe = Schreib_Ausgabe + "Für Batterieentladebegrenzung wurde NICHT " + str(Neu_Battery_MinRsvPct) +"% geschrieben, da NICHT \"schreiben\" übergeben wurde: \n"
                        else:
                            Schreib_Ausgabe = Schreib_Ausgabe + "Batterieentladebegrenzung hat sich nicht verändert, NICHTS zu schreiben!!\n"

                        if print_level >= 1:
                            print(Schreib_Ausgabe)

                        DEBUG_Ausgabe+="\nDEBUG <<<<<<<< ENDE ENTLADEBEGRENZUNG >>>>>>>>>>>>>"

                    # Wenn Pushmeldung aktiviert und Daten geschrieben an Dienst schicken
                    if (Push_Schreib_Ausgabe != "") and (Push_Message_EIN == 1):
                        Push_Message_Url = getVarConf('messaging','Push_Message_Url','str')
                        apiResponse = requests.post(Push_Message_Url, data=Push_Schreib_Ausgabe.encode(encoding='utf-8'), headers={ "Title": "Meldung Batterieladesteuerung!", "Tags": "sunny,zap" })
                        print("PushMeldung an ", Push_Message_Url, " gesendet.\n")


                    ######## PV Reservierung ENDE


                    # FALLBACK des Wechselrichters bei Ausfall der Steuerung
                    if Fallback_on != 0:
                        Fallback_Schreib_Ausgabe = ""
                        akt_Fallback_time = gen24.read_data('InOutWRte_RvrtTms_Fallback')
                        if Fallback_on == 2:
                            Fallback_Schreib_Ausgabe = Fallback_Schreib_Ausgabe + "Fallback ist eingeschaltet.\n"
                            DEBUG_Ausgabe+="\nDEBUG <<<<<<<< FALLBACK >>>>>>>>>>>>>"
                            Akt_Zeit_Rest = int(datetime.strftime(now, "%H%M")) % (Fallback_Zeitabstand_Std*100)
                            Fallback_Sekunden = int((Fallback_Zeitabstand_Std * 3600) + (Cronjob_Minutenabstand * 60 * 0.9))
                            # Zur vollen Fallbackstunde wenn noch kein Schreibzugriff war Fallback schreiben
                            if Akt_Zeit_Rest == 0 or akt_Fallback_time != Fallback_Sekunden:
                                if bereits_geschrieben == 0 or akt_Fallback_time != Fallback_Sekunden:
                                    if len(argv) > 1 and (argv[1] == "schreiben"):
                                        fallback_msg = gen24.write_data('InOutWRte_RvrtTms_Fallback', Fallback_Sekunden)
                                        Fallback_Schreib_Ausgabe = Fallback_Schreib_Ausgabe + "Fallback " + str(Fallback_Sekunden) + " geschrieben.\n"
                                        DEBUG_Ausgabe+="\nDEBUG Meldung FALLBACK schreiben: " + str(fallback_msg)
                                    else:
                                        Fallback_Schreib_Ausgabe = Fallback_Schreib_Ausgabe + "Fallback wurde NICHT geschrieben, da NICHT \"schreiben\" übergeben wurde:\n"
                                else:
                                    Fallback_Schreib_Ausgabe = Fallback_Schreib_Ausgabe + "Fallback wurde NICHT geschrieben, da bereits auf den WR geschrieben wurde.\n"

                        else:
                            Fallback_Schreib_Ausgabe = Fallback_Schreib_Ausgabe + "Fallback ist NICHT eingeschaltet.\n"
                            if akt_Fallback_time != 0:
                                if len(argv) > 1 and (argv[1] == "schreiben"):
                                    fallback_msg = gen24.write_data('InOutWRte_RvrtTms_Fallback', 0)
                                    Fallback_Schreib_Ausgabe = Fallback_Schreib_Ausgabe + "Fallback Deaktivierung geschrieben.\n"
                                    DEBUG_Ausgabe+="\nDEBUG Meldung FALLBACK Deaktivierung schreiben: " + str(fallback_msg)
                                else:
                                    Fallback_Schreib_Ausgabe = Fallback_Schreib_Ausgabe + "Fallback Deaktivierung NICHT geschrieben, da NICHT \"schreiben\" übergeben wurde:\n"

                        Fallback_Schreib_Ausgabe = Fallback_Schreib_Ausgabe + "InOutWRte_RvrtTms_Fallback: " + str(gen24.read_data('InOutWRte_RvrtTms_Fallback')) + "\n"
                        Fallback_Schreib_Ausgabe = Fallback_Schreib_Ausgabe + "StorageControlMode:    " + str(gen24.read_data('StorageControlMode')) + "\n"
                        DEBUG_Ausgabe+="\nDEBUG <<<<<<<< ENDE FALLBACK >>>>>>>>>>>>>"

                        if print_level >= 1:
                            print(Fallback_Schreib_Ausgabe)
                    # FALLBACK ENDE

                    ### LOGGING, Schreibt mit den übergebenen Daten eine CSV- oder SQlite-Datei
                    ## nur wenn "schreiben" oder "logging" übergeben worden ist
                    Logging_ein = getVarConf('Logging','Logging_ein','eval')
                    if Logging_ein == 1:
                        Logging_Schreib_Ausgabe = ""
                        if len(argv) > 1 and (argv[1] == "schreiben" or argv[1] == "logging"):
                            Logging_file = getVarConf('Logging','Logging_file','str')
                            API_Werte = gen24.get_API()
                            # In die DB werden die liftime Verbrauchszählerstände gespeichert
                            save_SQLite(Logging_file, API_Werte['AC_Produktion'], API_Werte['DC_Produktion'], API_Werte['Netzverbrauch'], API_Werte['Einspeisung'], API_Werte['Batterie_IN'], API_Werte['Batterie_OUT'], aktuelleVorhersage, BattStatusProz)
                            Logging_Schreib_Ausgabe = 'Daten wurden in die SQLite-Datei gespeichert!'
                        else:
                            Logging_Schreib_Ausgabe = "Logging wurde NICHT gespeichert, da NICHT \"logging\" oder \"schreiben\" übergeben wurde:\n" 

                        if print_level >= 1:
                            print(Logging_Schreib_Ausgabe)
                    # LOGGING ENDE



                    #DEBUG ausgeben
                    if print_level >= 2:
                        print(DEBUG_Ausgabe)
                    if print_level >= 1:
                        print("************* ENDE: ", datetime.now(),"************* \n")


            finally:
                    if (gen24 and not auto):
                            gen24.modbus.close()


        else:
            print(datetime.now())
            print("WR offline")

