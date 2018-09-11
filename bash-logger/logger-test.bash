#!/bin/bash

set -Eeuo pipefail

source logger.bash

export LOGGER_LOGFILE="logger-test.log"
export LOGGER_STDOUT_LEVEL=${LOG_LEVEL_WARN}
export LOGGER_STDERR_LEVEL=${LOG_LEVEL_ERROR}
rm -f "logger-test.log"

(
    echo "FATAL test, next line should be printed to stderr"
    FATAL "Testing FATAL"

    echo "ERROR test, next line should be printed to stderr"
    ERROR "Testing ERROR"

    echo "WARN test, next line should be printed to stdout"
    WARN "Testing WARN"

    echo "INFO test, this line should go only to logfile"
    INFO "Testing INFO"

    echo "Testign pipe functionality"
    echo "Piped into INFO" | INFO
) 2>logger-test-stderr.log >logger-test-stdout.log

