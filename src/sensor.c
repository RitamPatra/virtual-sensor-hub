#define _POSIX_C_SOURCE 200809L
#include "hub.h"
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <unistd.h>
#include <time.h>
#include <string.h>

typedef struct {
    int ms;
    int sensor_id; // 0=temp, 1=hum, 2=press
} sensor_arg_t;

static pthread_t t_temp, t_hum, t_press;

static void sleep_ms(int ms) {
    usleep(ms * 1000);
}
static long now_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    return ts.tv_sec * 1000L + ts.tv_nsec / 1000000L;
}

// get deterministic sequences of data using counters
static void *temp_thread(void *arg) {
    sensor_arg_t *a = (sensor_arg_t*)arg;
    int ms = a->ms;
    free(a);
    int cnt = 0;
    while (1) {
        // deterministic sequence: cycles from 22 to 36 degrees Celsius
        double v = 22.0 + (cnt % 15);
        long t = now_ms();
        hub_submit_sample("TEMP", v, t);
        cnt++;
        sleep_ms(ms);
    }
    return NULL;
}

static void *hum_thread(void *arg) {
    sensor_arg_t *a = (sensor_arg_t*)arg;
    int ms = a->ms;
    free(a);
    int cnt = 0;
    while (1) {
        // deterministic sequence: cycles from 40 to 95 percent humidity
        double v = 40.0 + (cnt % 56);
        long t = now_ms();
        hub_submit_sample("HUM", v, t);
        cnt++;
        sleep_ms(ms);
    }
    return NULL;
}

static void *press_thread(void *arg) {
    sensor_arg_t *a = (sensor_arg_t*)arg;
    int ms = a->ms;
    free(a);
    int cnt = 0;
    while (1) {
        // deterministic sequence: cycles from 995 to 1020 mb pressure
        double v = 995.0 + (cnt % 26);
        long t = now_ms();
        hub_submit_sample("PRESS", v, t);
        cnt++;
        sleep_ms(ms);
    }
    return NULL;
}

// create a thread for each measurement
void start_temp_sensor(int ms) {
    sensor_arg_t *a = malloc(sizeof(*a));
    a->ms = ms; a->sensor_id = 0;
    pthread_create(&t_temp, NULL, temp_thread, a);
}

void start_hum_sensor(int ms) {
    sensor_arg_t *a = malloc(sizeof(*a));
    a->ms = ms; a->sensor_id = 1;
    pthread_create(&t_hum, NULL, hum_thread, a);
}

void start_pressure_sensor(int ms) {
    sensor_arg_t *a = malloc(sizeof(*a));
    a->ms = ms; a->sensor_id = 2;
    pthread_create(&t_press, NULL, press_thread, a);
}
