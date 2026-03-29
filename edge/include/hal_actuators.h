#pragma once

#ifndef HYDROV_HAL_ACTUATORS_H_INCLUDED
#define HYDROV_HAL_ACTUATORS_H_INCLUDED

#include <Arduino.h>
#include "config.h"

struct ActuatorState_t {
    bool valve_reject_open;
    bool valve_intake_open;
    uint32_t last_state_change;
};

void initActuators();
void openValveReject();
void closeValveReject();
bool isValveRejectOpen();
void openValveIntake();
void closeValveIntake();
bool isValveIntakeOpen();
void stopAllValves();
ActuatorState_t getActuatorState();

#endif // HYDROV_HAL_ACTUATORS_H_INCLUDED