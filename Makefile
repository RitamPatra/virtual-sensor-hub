CC = gcc
CFLAGS = -std=c11 -Wall -Wextra -g
LDFLAGS = -pthread
SRC = src/main.c src/sensor.c src/hub.c
OBJ = $(SRC:.c=.o)
BIN = sensorhub

all: $(BIN)

$(BIN): $(OBJ)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJ) $(BIN) data/hub.log

.PHONY: all clean