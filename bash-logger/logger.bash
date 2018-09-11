#!/bin/bash

# Simple log facility for bash
# Inspired and adapted from
# https://github.com/idelsink/b-log/blob/master/b-log.sh
# Writes all output to a log file
# Optionally messages with high enough level can be outputted to stdout / stderr
# See logger-test.bash for usage examples

# Converntions All variables, function names etc. start with "LOGGER_".
# Variables, functions etc. that have fully upper case name are public
# interface. Variables, functions etc. that have partially lower case name are
# private to this file. Don't use them from other scripts


# Make sure this script is included only once
if [ -n "${LOGGER_sourced+x}" ]; then
  return
else
  readonly LOGGER_sourced=1
fi

# Available log levels. IF you modify these, use powers of 2 to make it possible
# to use them as bitmasks in the future
# TODO: maybe turn these around? LOG_LEVEL_OFF needs testing
readonly LOG_LEVEL_OFF=0      # none
readonly LOG_LEVEL_FATAL=1    # unusable, crash
readonly LOG_LEVEL_ERROR=2    # error conditions
readonly LOG_LEVEL_WARN=4     # warning conditions
readonly LOG_LEVEL_INFO=8     # informational

readonly LOGGER_log_levels=(
  "${LOG_LEVEL_FATAL}"  "FATAL"
  "${LOG_LEVEL_ERROR}"  "ERROR"
  "${LOG_LEVEL_WARN}"   "WARN"
  "${LOG_LEVEL_INFO}"   "INFO"
)
# log level array columns
readonly LOGGER_levels_level=0
readonly LOGGER_levels_name=1


# TODO: check that variables are set

function LOGGER_get_log_level_info() {
  # @description get the log level information
  # @param $1 log type
  # @return returns information in the variables
  # LOGGER_level_name

  local log_level=${1}

  local i=0
  for ((i=0; i<${#LOGGER_log_levels[@]}; i+=$((LOGGER_levels_name+1)))); do
    if [[ "$log_level" == "${LOGGER_log_levels[i]}" ]]; then
      LOGGER_level_name="${LOGGER_log_levels[i+${LOGGER_levels_name}]}"
      return 0
    fi
  done
  return 1
}

function LOGGER_write_log_message {
  # @description Write the log message to file and to appropriate output streams
  # @param $1 log type
  # $2... the rest are messages
  # If message argument is empty, read message from stdin

  log_level="${1}"
  LOGGER_get_log_level_info "${1}"

  shift
  local message=${*:-}
  if [ -z "$message" ]; then # if message is empty, get from stdin
    message="$(cat /dev/stdin)"
  fi

  message="$(date '+%Y-%m-%d %H:%M:%S') ${LOGGER_level_name}: $message"

  if [[ "$log_level" -le "$LOGGER_STDOUT_LEVEL" ]]; then
    if [[ "$log_level" -le "$LOGGER_STDERR_LEVEL" ]]; then
      echo -e "${message}" >&2
    else
      echo -e "${message}"
    fi
  fi

  echo -e "${message}" >> "${LOGGER_LOGFILE}"
}

# Logging functions
function FATAL { LOGGER_write_log_message ${LOG_LEVEL_FATAL} "$@"; }
function ERROR { LOGGER_write_log_message ${LOG_LEVEL_ERROR} "$@"; }
function WARN { LOGGER_write_log_message ${LOG_LEVEL_WARN} "$@"; }
function INFO { LOGGER_write_log_message ${LOG_LEVEL_INFO} "$@"; }