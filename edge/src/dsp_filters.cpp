#include "dsp_filters.h"
#include <movingAvg.h>

namespace {
	// Ventanas de filtrado definidas por arquitectura: turbidez=10, ultrasonico=5.
	movingAvg turbidityFilter(10);
	movingAvg ultrasonicFilter(5);
}

void initFilters() {
	turbidityFilter.begin();
	ultrasonicFilter.begin();
}

uint16_t getFilteredTurbidity(uint16_t rawValue) {
	return static_cast<uint16_t>(turbidityFilter.reading(static_cast<int>(rawValue)));
}

float getFilteredDistance(float rawValue) {
	if (rawValue < 0.0f) {
		return rawValue;
	}

	const int scaledRaw = static_cast<int>(rawValue * 100.0f);
	const int scaledFiltered = ultrasonicFilter.reading(scaledRaw);
	return static_cast<float>(scaledFiltered) / 100.0f;
}
