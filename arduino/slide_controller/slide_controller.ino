
// https://github.com/ArminJo/ServoEasing
#include "ServoEasing.hpp"

// for servo
int SERVO1_PIN = 9;
int SERVO2_PIN = 8;
ServoEasing Servo1;
ServoEasing Servo2;

// serial processing
String m_lastMessage;
unsigned long m_timeLastLedToggle = 0;
unsigned long m_toggleInterval = 1000;
bool m_ledOn;
bool m_motionRunning = false;
int m_lastRotationPosition = 0;

int m_servo_a_min = 90;
int m_servo_a_max = 170;
int m_servo_a_offset = 0;  // center, additive offset wrt. 90

int m_servo_b_min = 0;
int m_servo_b_max = 180;
int m_servo_b_offset = 2;  // center, additive offset wrt. 90

void setup() {
  // initialize LED_BUILTIN
  pinMode(LED_BUILTIN, OUTPUT);
  
  // initialize serial communication at 9600 bits per second:
  Serial.begin(9600);

  // init servo
  Servo1.attach(SERVO1_PIN, 45);
  Servo2.attach(SERVO2_PIN, 45);
  Servo1.write(90 + m_servo_a_offset); // star value middle
  Servo2.write(90 + m_servo_b_offset);
  Servo1.setEasingType(EASE_CUBIC_IN_OUT); // EASE_LINEAR is default
  Servo2.setEasingType(EASE_CUBIC_IN_OUT); // EASE_LINEAR is default
}

void loop() {
    // blink fast while moving
    if(Servo1.isMoving() || Servo2.isMoving()) {
      m_toggleInterval = 100;
    } else {
      m_toggleInterval = 1000;
    }

    // detect motion completed
    if(m_motionRunning && !Servo1.isMoving() && !Servo2.isMoving()) {
      m_motionRunning = false;
      Serial.println("GOT motion completed");
    }

    toggleLed();
    readSerial();
}

void readSerial() {
  while(Serial.available() > 0) {
    char c = Serial.read();

    // concatenate message until receiving '\n'
    if(c == 10) {
      processSerialMsg(m_lastMessage);
      
      m_lastMessage = "";
    } else {
      m_lastMessage += c;
    }
  }
}

void processSerialMsg(String msg) {
  String cmd = "";
  if(msg.length() >= 3) {
    cmd = msg.substring(0,3);
  }

  if(cmd == "HLO") {
    Serial.println("HLO slide-controller");

  } else if(cmd == "GOT") {  // GOT 90 90
    // arguments
    int firstSpace = msg.indexOf(' ');
    int secondSpace = msg.indexOf(' ', firstSpace+1);
    if(firstSpace == -1 || secondSpace == -1) {
      Serial.println("ERR unsupported GOT syntax (expected 'GOT 0 0' received '"+msg+"')");
      return;
    }
    String curvatureStr = msg.substring(firstSpace+1, secondSpace);
    String velocityStr = msg.substring(secondSpace+1);
    int servo_a_pos = curvatureStr.toInt();
    int servo_b_pos = velocityStr.toInt();
    if(servo_a_pos < m_servo_a_min || servo_a_pos > m_servo_a_max) {
      Serial.println(String("ERR servo_a_pos out of range (expected: [")+m_servo_a_min+"-"+m_servo_a_max+"] reiceived: '"+servo_a_pos+"')");
      return;
    }
    if(servo_b_pos < m_servo_b_min || servo_b_pos > m_servo_b_max) {
      Serial.println(String("ERR servo_b_pos out of range (expected: [")+m_servo_b_min+"-"+m_servo_b_max+"] reiceived: '"+servo_b_pos+"')");
      return;
    }

    //offsets
    servo_a_pos += m_servo_a_offset;
    servo_b_pos += m_servo_b_offset;
    servo_a_pos = max(m_servo_a_min, min(m_servo_a_max, servo_a_pos));
    servo_b_pos = max(m_servo_b_min, min(m_servo_b_max, servo_b_pos));

    // speed of rotation
    int rotationDelta = abs(m_lastRotationPosition - servo_b_pos);
    // Delta  Speed
    // 10     20
    // 180    50

    int speed = max(5, min(50, 15 + rotationDelta * 40 / 170));
    Serial.println(String("LOG rotationDelta=")+rotationDelta+" Speed="+speed);

    Serial.println("GOT success");

    m_lastRotationPosition = servo_b_pos;

    Servo1.startEaseTo(servo_a_pos, 60, START_UPDATE_BY_INTERRUPT);
    Servo2.startEaseTo(servo_b_pos, speed, START_UPDATE_BY_INTERRUPT);
    Serial.println("GOT success");
    m_motionRunning = true;

  } else {
    Serial.println("ERR unsupported cmd '"+msg+"'");
  } 
}

void toggleLed() {
  if(millis() - m_timeLastLedToggle > m_toggleInterval) {
    m_ledOn = !m_ledOn;
    m_timeLastLedToggle = millis();

    if(m_ledOn) {
      digitalWrite(LED_BUILTIN, HIGH);   // turn the LED on (HIGH is the voltage level)
    } else {
      digitalWrite(LED_BUILTIN, LOW);
    }
  }
}
                                                                                   