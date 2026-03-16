#ifndef DSP_FILTERS_H
#define DSP_FILTERS_H

#include <Arduino.h>

void initFilters();
uint16_t getFilteredTurbidity(uint16_t rawValue);
float getFilteredDistance(float rawValue);

#endif // DSP_FILTERS_H
