#include <Arduino.h>
#include "config.h"

// ============================================
// FLOW SENSOR - INTERRUPT HANDLER & VARIABLES
// ============================================
// Separamos los pulsos: unos para la velocidad instantánea y otros para el total histórico
volatile uint16_t currentFlowPulses = 0; 
volatile uint32_t totalFlowPulses = 0;

void IRAM_ATTR flowPulseCounter() {
    currentFlowPulses++;
    totalFlowPulses++; // Este nunca se borra al leer la velocidad
}

// ============================================
// SENSOR INITIALIZATION
// ============================================
void initSensors() {
    // Turbidity sensor
    pinMode(PIN_TURBIDITY_SENSOR, INPUT);
    
    // Ultrasonic sensor
    pinMode(PIN_ULTRASONIC_TRIG, OUTPUT);
    pinMode(PIN_ULTRASONIC_ECHO, INPUT);
    digitalWrite(PIN_ULTRASONIC_TRIG, LOW);
    
    // Flow sensor with hardware interrupt (FALLING es más estable para el imán del YF-S201)
    pinMode(PIN_FLOW_SENSOR, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(PIN_FLOW_SENSOR), flowPulseCounter, FALLING);
}

// ============================================
// ULTRASONIC SENSOR - NON-BLOCKING READ
// ============================================
float readUltrasonicDistance() {
    digitalWrite(PIN_ULTRASONIC_TRIG, LOW);
    delayMicroseconds(2);
    digitalWrite(PIN_ULTRASONIC_TRIG, HIGH);
    delayMicroseconds(10);
    digitalWrite(PIN_ULTRASONIC_TRIG, LOW);
    
    // 
    unsigned long duration = pulseIn(PIN_ULTRASONIC_ECHO, HIGH, ULTRASONIC_TIMEOUT_US);
    
    if (duration == 0) {
        return -1.0; 
    }
    
    return (duration * 0.0343) / 2.0;
}

// ============================================
// TURBIDITY SENSOR - ANALOG READ
// ============================================
uint16_t readTurbidityRaw() {
    return analogRead(PIN_TURBIDITY_SENSOR);
}

// ============================================
// FLOW SENSOR - CALCULATE FLOW RATE (LPM)
// ============================================
float readFlowRate(unsigned long intervalMs) {
    noInterrupts();
    uint16_t pulses = currentFlowPulses;
    currentFlowPulses = 0; // Solo reseteamos los pulsos temporales
    interrupts();
    
    if (intervalMs == 0) {
        return 0.0;
    }
    
    float liters = (float)pulses / FLOW_PULSES_PER_LITER;
    float minutes = intervalMs / 60000.0;
    
    return liters / minutes;
}

// ============================================
// FLOW SENSOR - GET TOTAL VOLUME (Liters)
// ============================================
float getFlowTotalLiters() {
    noInterrupts();
    uint32_t totalPulses = totalFlowPulses;
    interrupts();
    
    return (float)totalPulses / FLOW_PULSES_PER_LITER;
}

// ============================================
// FLOW SENSOR - RESET TOTAL COUNTER
// ============================================
void resetFlowCounter() {
    noInterrupts();
    currentFlowPulses = 0;
    totalFlowPulses = 0;
    interrupts();
}