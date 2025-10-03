#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <unistd.h>
#include <string.h>
#include <pthread.h>

#include "hub.h"
#include "sensor.h"

static volatile int keep_running = 1;
void sigint_handler(int sig) { (void)sig; keep_running = 0; }

// watcher which stops after specified duration
static void *watcher(void *arg) {
    int ms = *(int*)arg;
    free(arg);
    usleep(ms * 1000);
    keep_running = 0;
    return NULL;
}

int main(int argc, char **argv) {
    signal(SIGINT, sigint_handler);

    int test_duration_ms = 0;
    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--test-duration") == 0 && i+1 < argc) {
            test_duration_ms = atoi(argv[i+1]) * 1000; // arg is in seconds
            i++;
        }
    }

    if (!hub_init("data/hub.log")) {
        fprintf(stderr, "hub_init failed\n");
        return 1;
    }

    start_hub_processor();

    //sensor sampling rates (in milliseconds)
    start_temp_sensor(500);     
    start_hum_sensor(700);
    start_pressure_sensor(1200);

    pthread_t watcher_id = 0;
    if (test_duration_ms > 0) {
        int *p = malloc(sizeof(int));
        *p = test_duration_ms;
        pthread_create(&watcher_id, NULL, watcher, p);
    }

    printf("The sensor hub is running. Press Ctrl+C to stop.\n");
    while (keep_running) {
        sleep(1);
    }

    printf("Shutting down...\n");
    hub_processor_stop(); // cleanly stop processor thread
    hub_shutdown();

    if (test_duration_ms > 0) {
        pthread_join(watcher_id, NULL);
    }

    printf("Exited.\n");
    return 0;
}
