#!/bin/sh
#
# Script restore backed up configuration files
#
# Do this after updating from git
#
cp config-copy.json config.json
cp coverMetas-copy.json coverMetas.json
cp stationLogos-copy.json stationLogos.json
