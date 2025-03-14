= CNC-Shieldv3 / GRBLv1.1

== Info
* Uninstall brltty package because it interfers with Arduinos UART USB interface
  sudo apt remove brltty
* Connect Enable-Pin to ground
* Left most cable is top at board
* Universal G-Code sender configuration
    * Firmware: GRBL (no ESP32)
    * Port ttyUSB0
    * Baud: 115200

== Power Supply
* 12V

== Parameters
* Acceleration
    $120=15.000
    $121=15.000
* Velocity
    $110=300  # works with 12V
    $111=300
    $110=1000  # works with 20V
    $111=1000
* Relative Motion Command
    G21G91X1Y0

$100 = 200.000    (X-axis travel resolution, step/mm)
$101 = 200.000    (Y-axis travel resolution, step/mm)
$102 = 200.000    (Z-axis travel resolution, step/mm)
$110 = 200.000    (X-axis maximum rate, mm/min)
$111 = 200.000    (Y-axis maximum rate, mm/min)
$112 = 3000.000    (Z-axis maximum rate, mm/min)
$120 = 10.000    (X-axis acceleration, mm/sec^2)
$121 = 10.000    (Y-axis acceleration, mm/sec^2)
$122 = 500.000    (Z-axis acceleration, mm/sec^2)
$130 = 762.000    (X-axis maximum travel, millimeters)
$131 = 812.000    (Y-axis maximum travel, millimeters)
$132 = 105.000    (Z-axis maximum travel, millimeters)

== G-Code Commands
* G21  Set to millimeters
* G92X0Y0  Set current position to be called 0/0
* G90 G1 X0Y0 F100  Absolute mode move to 0/0
* G91X1Y1           Incremental move by 1/1

== How to compile GRBL from source
* Base Version
    * Connect arduino multiple times until dmesg says connected to /dev/ttyUSB0
    * Set board mode to Arduino UNO
    * Download grbl source from [github](https://github.com/gnea/grbl/releases)
    * Extract
    * Inside the folder take the "grbl" folder and compress as zip
    * In Arduino IDE
    * Go to Sketch > Include Library > Add .ZIP Library ...
    * Re-Start Arduino IDE
    * The library is now at /home/USERNAME/Arduino/libraries/grbl/
    * Go to File > Examples > grbl > grbl Upload
    * Compile & Upload to Arduino

* Enable CoreXY Mode
    * Navigate to #include <grbl.h> -> F12 Go to definition
    * Navigate to #include <config.h> -> F12 go to definition
    * Find // #define COREXY // Default disabled. Uncomment to enable.
    * Compile & Upload to Arduino
