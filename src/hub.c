#define _POSIX_C_SOURCE 200809L
#include "hub.h"
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <stdint.h>
#include <errno.h>

#define QUEUE_SIZE 1024
#define WINDOW_SIZE 5
#define MAX_TYPE_LEN 16
#define NUM_SENSOR_TYPES 3

// thresholds for moving-average alerts
static const double THRESHOLD_TEMP = 28.0;
static const double THRESHOLD_HUM  = 80.0;
static const double THRESHOLD_PRESS = 1015.0;

// sensor type mapping
enum sensor_id { SENSOR_TEMP = 0, SENSOR_HUM = 1, SENSOR_PRESS = 2 };

// struct for sample readings
typedef struct {
    char type[MAX_TYPE_LEN]; /* "TEMP", "HUM", "PRESS" */
    double value;
    long ms_timestamp;
} sample_t;

// queue (sensors will place readings into this and hub processor will extract readings from here)
static sample_t queue[QUEUE_SIZE];
static size_t q_head = 0, q_tail = 0;
static pthread_mutex_t qlock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t qcond = PTHREAD_COND_INITIALIZER;

// logging
static FILE *logf = NULL;
static pthread_mutex_t loglock = PTHREAD_MUTEX_INITIALIZER;

// current time in ms
static long now_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    return ts.tv_sec * 1000L + ts.tv_nsec / 1000000L;
}

// enqueue (called by sensors)
void hub_submit_sample(const char *type, double value, long ms_timestamp) {
    pthread_mutex_lock(&qlock);
    size_t next = (q_tail + 1) % QUEUE_SIZE;
    if (next == q_head) {
        // drop the sample if the queue is full
        pthread_mutex_unlock(&qlock);
        return;
    }
    strncpy(queue[q_tail].type, type, MAX_TYPE_LEN-1);
    queue[q_tail].type[MAX_TYPE_LEN-1] = '\0';
    queue[q_tail].value = value;
    queue[q_tail].ms_timestamp = ms_timestamp;
    q_tail = next;
    pthread_cond_signal(&qcond);
    pthread_mutex_unlock(&qlock);

    // also write raw sample line to log for trace
    pthread_mutex_lock(&loglock);
    if (logf) {
        fprintf(logf, "SAMPLE|%s|%.3f|%ld\n", type, value, ms_timestamp);
        fflush(logf);
    }
    pthread_mutex_unlock(&loglock);
}

bool hub_init(const char *logpath) {
    logf = fopen(logpath, "w");
    if (!logf) return false;
    return true;
}

void hub_shutdown(void) {
    pthread_mutex_lock(&qlock);
    pthread_cond_broadcast(&qcond);
    pthread_mutex_unlock(&qlock);

    if (logf) {
        fclose(logf);
        logf = NULL;
    }
}

// processor thread: consumes samples, maintains moving average window per sensor 
static pthread_t processor_thread_id;
static volatile int processor_running = 1;

static int sensor_index_for_type(const char *type) {
    if (strcmp(type, "TEMP") == 0) return SENSOR_TEMP;
    if (strcmp(type, "HUM") == 0) return SENSOR_HUM;
    if (strcmp(type, "PRESS") == 0) return SENSOR_PRESS;
    return -1;
}

static void log_alert(const char *type, double avg, long ms_timestamp) {
    pthread_mutex_lock(&loglock);
    if (logf) {
        fprintf(logf, "ALERT|%s|%.3f|%ld|THRESHOLD_EXCEEDED\n", type, avg, ms_timestamp);
        fflush(logf);
    }
    pthread_mutex_unlock(&loglock);
}

static void *processor_main(void *arg) {
    (void)arg;
    // circular windows
    double windows[NUM_SENSOR_TYPES][WINDOW_SIZE];
    int win_counts[NUM_SENSOR_TYPES] = {0};
    int win_idx[NUM_SENSOR_TYPES] = {0};
    double win_sums[NUM_SENSOR_TYPES] = {0.0};
    memset(windows, 0, sizeof(windows));

    while (processor_running) {
        // pop one sample (wait if empty)
        pthread_mutex_lock(&qlock);
        while (q_head == q_tail && processor_running) {
            pthread_cond_wait(&qcond, &qlock);
        }
        if (!processor_running) {
            pthread_mutex_unlock(&qlock);
            break;
        }
        sample_t s = queue[q_head];
        q_head = (q_head + 1) % QUEUE_SIZE;
        pthread_mutex_unlock(&qlock);

        int idx = sensor_index_for_type(s.type);
        if (idx < 0) continue;

        // update moving window
        if (win_counts[idx] < WINDOW_SIZE) {
            // just add if window is not full yet
            windows[idx][win_idx[idx]] = s.value;
            win_sums[idx] += s.value;
            win_counts[idx]++;
            win_idx[idx] = (win_idx[idx] + 1) % WINDOW_SIZE;
        } else {
            // window is full: subtract oldest and add new 
            double old = windows[idx][win_idx[idx]];
            win_sums[idx] -= old;
            windows[idx][win_idx[idx]] = s.value;
            win_sums[idx] += s.value;
            win_idx[idx] = (win_idx[idx] + 1) % WINDOW_SIZE;
        }

        double avg = win_sums[idx] / (win_counts[idx] > 0 ? win_counts[idx] : 1);

        // check thresholds and log an alert if necessary
        if (idx == SENSOR_TEMP && win_counts[idx] == WINDOW_SIZE && avg > THRESHOLD_TEMP) {
            log_alert("TEMP", avg, s.ms_timestamp);
        } else if (idx == SENSOR_HUM && win_counts[idx] == WINDOW_SIZE && avg > THRESHOLD_HUM) {
            log_alert("HUM", avg, s.ms_timestamp);
        } else if (idx == SENSOR_PRESS && win_counts[idx] == WINDOW_SIZE && avg > THRESHOLD_PRESS) {
            log_alert("PRESS", avg, s.ms_timestamp);
        }

    }
    return NULL;
}

void start_hub_processor(void) {
    processor_running = 1;
    pthread_create(&processor_thread_id, NULL, processor_main, NULL);
}

// Function to request processor stop (used on shutdown)
void hub_processor_stop(void) {
    processor_running = 0;
    pthread_cond_broadcast(&qcond);
    pthread_join(processor_thread_id, NULL);
}
