<!doctype html>
<html>
    <head>
    <script src="chart.js"></script>
    <style>
    html, body {
        height: 98%;
        margin: 0px;
    }
    .container {
        height: 100%;
    }
    .navi {
    cursor:pointer;
    color:#000000;
    font-family:Arial;
    font-size: 150%;
    padding:6px 11px;
  }
  table {
  width: 95%;
  border: 1px solid;
  position: absolute;
  }
  td {
  white-space: nowrap;
  font-family: Arial;
  }

</style>
    </head>
    <body>


<?php
include "config.php";
# Prüfen ob SQLite Voraussetzungen vorhanden sind
$SQLite_file = "../" . $python_config['Logging']['Logging_file'];
if (!file_exists($SQLite_file)) {
    echo "\nSQLitedatei $filename existiert nicht, keine Grafik verfügbar!";
    echo "</body></html>";
    exit();
}

function schalter_ausgeben ( $case, $nextcase , $heute, $DiaTag, $Tag_davor, $Tag_danach, $AC_Produktion, $buttoncolor)
{

# Schalter zum Blättern usw.
echo '<table><tr><td>';
echo '<form method="POST" action="'.$_SERVER["PHP_SELF"].'">'."\n";
echo '<input type="hidden" name="DiaTag" value="'.$Tag_davor.'">'."\n";
echo '<input type="hidden" name="case" value="'.$case.'">'."\n";
echo '<button type="submit" class="navi"> &nbsp;&lt;&lt;&nbsp;</button>';
echo '</form>'."\n";

echo '</td><td>';
echo '<form method="POST" action="'.$_SERVER["PHP_SELF"].'">'."\n";
echo '<input type="hidden" name="DiaTag" value="'.$heute.'">'."\n";
echo '<input type="hidden" name="case" value="'.$case.'">'."\n";
echo '<button type="submit" class="navi"> '.$DiaTag.' </button>';
echo '</form>'."\n";

echo '</td><td>';
echo '<form method="POST" action="'.$_SERVER["PHP_SELF"].'">'."\n";
echo '<input type="hidden" name="DiaTag" value="'.$Tag_danach.'">'."\n";
echo '<input type="hidden" name="case" value="'.$case.'">'."\n";
echo '<button type="submit" class="navi"> &nbsp;&gt;&gt;&nbsp; </button>';
echo '</form>'."\n";

echo '</td><td>';
echo '<form method="POST" action="'.$_SERVER["PHP_SELF"].'">'."\n";
echo '<input type="hidden" name="DiaTag" value="'.$DiaTag.'">'."\n";
echo '<input type="hidden" name="case" value="'.$nextcase.'">'."\n";
echo '<button type="submit" class="navi" style="background-color:'.$buttoncolor.'"> '.$nextcase.'&gt;&gt; </button>';
echo '</form>'."\n";


echo '</td><td style="text-align:right; width: 100%; font-size: 170%">';
echo "$AC_Produktion KWh(AC)";

echo '</td></tr></table><br>';
}


# Diagrammtag festlegen
$heute = date("Y-m-d");
$DiaTag = $heute;
if (isset($_POST["DiaTag"])) $DiaTag = $_POST["DiaTag"];
$Tag_davor = date("Y-m-d",(strtotime("-1 day", strtotime($DiaTag))));
$Tag_danach = date("Y-m-d",(strtotime("+1 day", strtotime($DiaTag))));


# case = Verbrauch oder Produktion
$case = 'Produktion';
if (isset($_POST["case"])) $case = $_POST["case"];


$db = new SQLite3($SQLite_file);

# switch Verbrauch oder Produktion
switch ($case) {
    case 'Produktion':

# AC Produktion 
$SQL = "SELECT 
        MAX(AC_Produktion)- MIN(AC_Produktion) + 
        MAX(Batterie_IN) - min(Batterie_IN) + 
        MIN (Batterie_OUT) - MAX (Batterie_OUT)
        AS AC_Produktion
from pv_daten where Zeitpunkt LIKE '".$DiaTag."%'";
$AC_Produktion = round($db->querySingle($SQL)/1000, 1);

# Schalter aufrufen
schalter_ausgeben('Produktion', 'Verbrauch', $heute, $DiaTag, $Tag_davor, $Tag_danach, $AC_Produktion, 'red');

# ProduktionsSQL
$SQL = "WITH Alle_PVDaten AS (
		select	Zeitpunkt,
		ROUND((JULIANDAY(Zeitpunkt) - JULIANDAY(LAG(Zeitpunkt) OVER(ORDER BY Zeitpunkt))) * 1440) AS Zeitabstand,
		((AC_Produktion - LAG(AC_Produktion) OVER(ORDER BY Zeitpunkt)) - (Einspeisung - LAG(Einspeisung) OVER(ORDER BY Zeitpunkt)) - (Batterie_OUT - LAG(Batterie_OUT) OVER(ORDER BY Zeitpunkt))) AS Direktverbrauch,
		((Netzverbrauch - LAG(Netzverbrauch) OVER(ORDER BY Zeitpunkt)) + (AC_Produktion - LAG(AC_Produktion) OVER(ORDER BY Zeitpunkt)) - (Einspeisung - LAG(Einspeisung) OVER(ORDER BY Zeitpunkt))) AS Gesamtverbrauch,
		(Einspeisung - LAG(Einspeisung) OVER(ORDER BY Zeitpunkt)) AS Einspeisung,
		((Batterie_IN - LAG(Batterie_IN) OVER(ORDER BY Zeitpunkt)) - (Batterie_OUT - LAG(Batterie_OUT) OVER(ORDER BY Zeitpunkt))) AS BatteriePower,
		Vorhersage,
		BattStatus
from pv_daten where Zeitpunkt LIKE '".$DiaTag."%')
SELECT Zeitpunkt,
	Direktverbrauch*60/Zeitabstand AS Direktverbrauch,
	Gesamtverbrauch*60/Zeitabstand AS Gesamtverbrauch,
	Einspeisung*60/Zeitabstand AS Einspeisung,
	BatteriePower*60/Zeitabstand AS BatteriePower,
	Vorhersage,
	BattStatus
FROM Alle_PVDaten
Where Zeitabstand > 4";

$results = $db->query($SQL);

$optionen = array();
$optionen['Gesamtverbrauch']=['Farbe'=>'rgba(72,118,255,1)','fill'=>'false','stack'=>'1','linewidth'=>'2','order'=>'0','borderDash'=>'[0,0]','yAxisID'=>'y'];
$optionen['Vorhersage']=['Farbe'=>'rgba(255,140,05,1)','fill'=>'false','stack'=>'2','linewidth'=>'2','order'=>'0','borderDash'=>'[15,8]','yAxisID'=>'y'];
$optionen['BattStatus']=['Farbe'=>'rgba(34,139,34,1)','fill'=>'false','stack'=>'3','linewidth'=>'2','order'=>'0','borderDash'=>'[0,0]','yAxisID'=>'y2'];
$optionen['Einspeisung'] = ['Farbe' => 'rgba(148,148,148,1)', 'fill' => 'true', 'stack' => '0', 'linewidth' => '0', 'order' => '3', 'borderDash' => '[0, 0]', 'yAxisID' => 'y'];
$optionen['BatteriePower'] = ['Farbe' => 'rgba(50,205,50,1)', 'fill' => 'true', 'stack' => '0', 'linewidth' => '0', 'order' => '2', 'borderDash' => '[0, 0]', 'yAxisID' => 'y'];
$optionen['Direktverbrauch'] = ['Farbe' => 'rgba(255,215,0,1)', 'fill' => 'true', 'stack' => '0', 'linewidth' => '0', 'order' => '1', 'borderDash' => '[0, 0]', 'yAxisID' => 'y'];

$trenner = "";
$labels = "";
$daten = array();
while ($row = $results->fetchArray(SQLITE3_ASSOC)) {
        $first = true;
        foreach($row as $x => $val) {
        if ( $first ){
            # Datum zuschneiden 
            $label_element = substr($val, 11, -3);
            $labels = $labels.$trenner.'"'.$label_element.'"';
            $first = false;
        } else {
            if (!isset($daten[$x])) $daten[$x] = "";
            if ($x == 'Gesamtverbrauch' and $val < 0) $val = 0;
            if ($x == 'BatteriePower' and $val < 0) $val = 0;
            if ($x == 'Einspeisung' and $val < 0) $val = 0;
            if ($x == 'Direktverbrauch' and $val < 0) $val = 0;
            $daten[$x] = $daten[$x] .$trenner.$val;
            }
        }
$trenner = ",";
}
    break; # ENDE case Produktion

    case 'Verbrauch':

# AC Verbrauch
$SQL = "SELECT 
        MAX(Netzverbrauch)- MIN(Netzverbrauch) + 
        MAX(AC_Produktion) - min(AC_Produktion) + 
        MIN (Einspeisung) - MAX (Einspeisung)
        AS AC_Produktion
from pv_daten where Zeitpunkt LIKE '".$DiaTag."%'";
$AC_Verbrauch = round($db->querySingle($SQL)/1000, 1);

# Schalter aufrufen
schalter_ausgeben('Verbrauch', 'Produktion', $heute, $DiaTag, $Tag_davor, $Tag_danach, $AC_Verbrauch, 'green');

# VerbrauchSQL
$SQL = "WITH Alle_PVDaten AS (
		select	Zeitpunkt,
		ROUND((JULIANDAY(Zeitpunkt) - JULIANDAY(LAG(Zeitpunkt) OVER(ORDER BY Zeitpunkt))) * 1440) AS Zeitabstand,
        ((AC_Produktion - LAG(AC_Produktion) OVER(ORDER BY Zeitpunkt)) - (Einspeisung - LAG(Einspeisung) OVER(ORDER BY Zeitpunkt)) - (Batterie_OUT - LAG(Batterie_OUT) OVER(ORDER BY Zeitpunkt))) AS Direktverbrauch,
		(Netzverbrauch - LAG(Netzverbrauch) OVER(ORDER BY Zeitpunkt)) AS Netzverbrauch,
		(AC_Produktion - LAG(AC_Produktion) OVER(ORDER BY Zeitpunkt)) + (Batterie_IN - LAG(Batterie_IN) OVER(ORDER BY Zeitpunkt)) - (Batterie_OUT - LAG(Batterie_OUT) OVER(ORDER BY Zeitpunkt)) AS Produktion,
		((Batterie_OUT - LAG(Batterie_OUT) OVER(ORDER BY Zeitpunkt)) - (Batterie_IN - LAG(Batterie_IN) OVER(ORDER BY Zeitpunkt))) AS VonBatterie,
		BattStatus
from pv_daten where Zeitpunkt LIKE '".$DiaTag."%')
SELECT Zeitpunkt,
	Direktverbrauch*60/Zeitabstand AS Direktverbrauch,
	Produktion*60/Zeitabstand AS Produktion,
	Netzverbrauch*60/Zeitabstand AS Netzverbrauch,
	VonBatterie*60/Zeitabstand AS VonBatterie,
	BattStatus
FROM Alle_PVDaten
Where Zeitabstand > 4";

$results = $db->query($SQL);

$optionen = array();
$optionen['Produktion']=['Farbe'=>'rgba(255,215,0,1)','fill'=>'false','stack'=>'1','linewidth'=>'2','order'=>'0','borderDash'=>'[0,0]','yAxisID'=>'y'];
$optionen['BattStatus']=['Farbe'=>'rgba(34,139,34,1)','fill'=>'false','stack'=>'3','linewidth'=>'2','order'=>'0','borderDash'=>'[0,0]','yAxisID'=>'y2'];
$optionen['Netzverbrauch'] = ['Farbe' => 'rgba(148,148,148,1)', 'fill' => 'true', 'stack' => '0', 'linewidth' => '0', 'order' => '3', 'borderDash' => '[0, 0]', 'yAxisID' => 'y'];
$optionen['VonBatterie'] = ['Farbe' => 'rgba(50,205,50,1)', 'fill' => 'true', 'stack' => '0', 'linewidth' => '0', 'order' => '2', 'borderDash' => '[0, 0]', 'yAxisID' => 'y'];
$optionen['Direktverbrauch'] = ['Farbe' => 'rgba(255,215,0,1)', 'fill' => 'true', 'stack' => '0', 'linewidth' => '0', 'order' => '1', 'borderDash' => '[0, 0]', 'yAxisID' => 'y'];

$trenner = "";
$labels = "";
$daten = array();
while ($row = $results->fetchArray(SQLITE3_ASSOC)) {
        $first = true;
        foreach($row as $x => $val) {
        if ( $first ){
            # Datum zuschneiden 
            $label_element = substr($val, 11, -3);
            $labels = $labels.$trenner.'"'.$label_element.'"';
            $first = false;
        } else {
            if (!isset($daten[$x])) $daten[$x] = "";
            if ($x == 'Produktion' and $val < 0) $val = 0;
            if ($x == 'VonBatterie' and $val < 0) $val = 0;
            if ($x == 'Netzverbrauch' and $val < 0) $val = 0;
            if ($x == 'Direktverbrauch' and $val < 0) $val = 0;
            $daten[$x] = $daten[$x] .$trenner.$val;
            }
        }
$trenner = ",";
}
    break; # ENDE case Verbrauch
    
} # ENDE switch
$db->close();
?>
<div class="container">
  <canvas id="PVDaten" style="height:100vh; width:100vw"></canvas>
</div>
<script>
new Chart("PVDaten", {
    type: 'line',
    data: {
      labels: [<?php echo $labels; ?>],
      datasets: [{
<?php
      $trenner = "";
      foreach($daten as $x => $val) {
      echo $trenner;
      echo "label: '$x',\n";
      echo "data: [ $val ],\n";
      echo "borderColor: '".$optionen[$x]['Farbe']."',\n";
      echo "backgroundColor: '".$optionen[$x]['Farbe']."',\n";
      echo "borderWidth: '".$optionen[$x]['linewidth']."',\n";
      echo "borderDash: ".$optionen[$x]['borderDash'].",\n";
      echo "pointRadius: 0,\n";
      echo "cubicInterpolationMode: 'monotone',\n";
      echo "fill: ".$optionen[$x]['fill'].",\n";
      echo "stack: '".$optionen[$x]['stack']."',\n";
      echo "order: '".$optionen[$x]['order']."',\n";
      echo "yAxisID: '".$optionen[$x]['yAxisID']."'\n";
      $trenner = "},{\n";
      }
?>
    }]
    },
    options: {
      responsive: true,
      interaction: {
        intersect: false,
        mode: 'index',
        },
      plugins: {
        title: {
            display: true,
            //text: (ctx) => 'Tooltip position mode: ' + ctx.chart.options.plugins.tooltip.position,
        },
      },
    scales: {
      x: {
        ticks: {
          /*
          // Hier nur jede 6te Beschriftung ausgeben
          // For a category axis, the val is the index so the lookup via getLabelForValue is needed
          callback: function(val, index) {
            // nur halbe Stunden in der X-Beschriftung ausgeben
            return index % 6 === 0 ? this.getLabelForValue(val) : '';
          },
          */
          font: {
             size: 20,
           }
        }
      },
      y: {
        type: 'linear', // only linear but allow scale type registration. This allows extensions to exist solely for log scale for instance
        position: 'left',
        stacked: true,
        ticks: {
           font: {
             size: 20,
           }
        }
      },
      y2: {
        type: 'linear', // only linear but allow scale type registration. This allows extensions to exist solely for log scale for instance
        position: 'right',
        reverse: false,
        min: 0,
        max: 100,
        ticks: {
           font: {
             size: 20,
           }
        }
      },
    }
    },
  });
</script>

    </body>
</html>
