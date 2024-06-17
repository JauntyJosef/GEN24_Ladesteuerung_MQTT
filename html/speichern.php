<?php

include "config.php";

$EV = array();
$Tag_Zeit = $_POST["Tag_Zeit"];
$Feld1 = $_POST['Res_Feld1'];
$Feld2 = $_POST['Res_Feld2'];

if(isset($_POST["Tag_Zeit"]))
{
 for($count = 0; $count < count($Tag_Zeit); $count++)
 {
 $EV[$Tag_Zeit[$count]]['Res_Feld1']=$Feld1[$count];
 $EV[$Tag_Zeit[$count]]['Res_Feld2']=$Feld2[$count];
 $Watt[$Tag_Zeit[$count]]=(float) $Feld1[$count]*1000 + (float) $Feld2[$count]*1000;
 }
}

file_put_contents($ReservierungsFile, json_encode($EV, JSON_PRETTY_PRINT));
file_put_contents($WattReservierungsFile, json_encode($Watt, JSON_PRETTY_PRINT));


// NEU
// Laden und Decodieren des JSON-Dokuments in ein Array
/* $AV = json_decode(file_get_contents($ReservierungsFile), true);

//Steuerungsfile schreiben
if($steuerung_value !== null) {
    $steuerung_data = ['Steuerung' => $steuerung_value];
    file_put_contents($SteuerungsFile, json_encode($steuerung_data, JSON_PRETTY_PRINT));
}
//Steuerung MQTT senden
$pythonSkript = '/home/GEN24/Steuerung_mqtt_senden.py';
    $command = 'python3 ' . $pythonSkript . ' ' . escapeshellarg($steuerung_value);
    exec($command);

// Überprüfen, ob "ManuelleSteuerung" im Array vorhanden ist
if(isset($AV["ManuelleSteuerung"])) {
    // Extrahieren des Wertes von "Res_Feld1" für "ManuelleSteuerung"
    $manuelleSteuerungResFeld1 = $AV["ManuelleSteuerung"]["Res_Feld1"];
    // Übergeben des Wertes an das Python-Skript
    // Hier ein Beispiel, wie Sie den Wert an Python übergeben könnten
    $pythonSkript = '/home/GEN24/LadeEntlade_mqtt_senden.py';
    $command = 'python3 ' . $pythonSkript . ' ' . escapeshellarg($manuelleSteuerungResFeld1);
    exec($command);
} */
?>
