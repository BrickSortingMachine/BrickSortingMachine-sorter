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
* Before Calibration
    * Acceleration
        $120=15.000
        $121=15.000
    * Velocity
        $110=1000  # works with 20V
        $111=1000
* After Calibration
    * Acceleration
        $120=1000
        $121=1000
    * Velocity
        * axis-aligned motions
            $110=150000  # works with 20V
            $111=150000
        * diagonal motions
            $110=50000
            $111=50000
* Relative Motion Command
    G21G91X1Y0



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

* Enable Homing Force Set Origin to 0/0/0
    * Navigate to #include <grbl.h> -> F12 Go to definition
    * Navigate to #include <config.h> -> F12 go to definition
    * Find HOMING_FORCE_SET_ORIGIN Uncomment to enable
    * Compile & Upload to Arduino

Backup Values:
>>> $$
$0 = 10    (Step pulse time, microseconds)
$1 = 100    (Step idle delay, milliseconds)
$2 = 1    (Step pulse invert, mask)
$3 = 5    (Step direction invert, mask)
$4 = 1    (Invert step enable pin, boolean)
$5 = 0    (Invert limit pins, boolean)
$6 = 0    (Invert probe pin, boolean)
$10 = 1    (Status report options, mask)
$11 = 0.010    (Junction deviation, millimeters)
$12 = 0.002    (Arc tolerance, millimeters)
$13 = 0    (Report in inches, boolean)
$20 = 1    (Soft limits enable, boolean)
$21 = 1    (Hard limits enable, boolean)
$22 = 1    (Homing cycle enable, boolean)
$23 = 3    (Homing direction invert, mask)
$24 = 2000.000    (Homing locate feed rate, mm/min)
$25 = 8000.000    (Homing search seek rate, mm/min)
$26 = 250    (Homing switch debounce delay, milliseconds)
$27 = 30.000    (Homing switch pull-off distance, millimeters)
$30 = 30000    (Maximum spindle speed, RPM)
$31 = 0    (Minimum spindle speed, RPM)
$32 = 0    (Laser-mode enable, boolean)
$100 = 5.010    (X-axis travel resolution, step/mm)
$101 = 5.010    (Y-axis travel resolution, step/mm)
$102 = 5.010    (Z-axis travel resolution, step/mm)
$110 = 50000.000    (X-axis maximum rate, mm/min)
$111 = 50000.000    (Y-axis maximum rate, mm/min)
$112 = 3000.000    (Z-axis maximum rate, mm/min)
$120 = 1000.000    (X-axis acceleration, mm/sec^2)
$121 = 1000.000    (Y-axis acceleration, mm/sec^2)
$122 = 500.000    (Z-axis acceleration, mm/sec^2)
$130 = 1000.000    (X-axis maximum travel, millimeters)
$131 = 450.000    (Y-axis maximum travel, millimeters)
$132 = 105.000    (Z-axis maximum travel, millimeters)
ok
