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
 //print_r($Tag_Zeit[$count);
 $EV[$Tag_Zeit[$count]]['Res_Feld1']=(float) $Feld1[$count]*1000;
 $EV[$Tag_Zeit[$count]]['Res_Feld2']=(float) $Feld2[$count]*1000;
 }
}

file_put_contents($EntLadeSteuerFile, json_encode($EV, JSON_PRETTY_PRINT));


// Laden und Decodieren des JSON-Dokuments in ein Array
$AV = json_decode(file_get_contents($EntLadeSteuerFile), true);

// Laden und Decodieren des JSON-Dokuments in ein Array
$AV = json_decode(file_get_contents($EntLadeSteuerFile), true);

// Überprüfen, ob "ManuelleSteuerung" im Array vorhanden ist
if(isset($AV["ManuelleEntladesteuerung"])) {
    // Extrahieren des Wertes von "Res_Feld1" für "ManuelleSteuerung"
    $manuelleSteuerungResFeld1 = $AV["ManuelleEntladesteuerung"]["Res_Feld1"];
    // Übergeben des Wertes an das Python-Skript
    // Hier ein Beispiel, wie Sie den Wert an Python übergeben könnten
    echo "After if: $manuelleSteuerungResFeld1\n";
    if($manuelleSteuerungResFeld1 == "0") {
        $manuelleSteuerungResFeld1 = "AUS";
    }
    echo "After if: $manuelleSteuerungResFeld1\n";
    $pythonSkript = '/home/GEN24/LadeEntlade_mqtt_senden.py';
    $command = 'python3 ' . $pythonSkript . ' ' . escapeshellarg($manuelleSteuerungResFeld1);
    exec($command);
}

?>
