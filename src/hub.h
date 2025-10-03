#ifndef HUB_H
#define HUB_H
#include <stdbool.h>

bool hub_init(const char *logpath);
void hub_shutdown(void);

// API used by sensors
void hub_submit_sample(const char *type, double value, long ms_timestamp);

// Start processor thread
void start_hub_processor(void);

// Stop processor thread
void hub_processor_stop(void);

#endif