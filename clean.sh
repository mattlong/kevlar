#!/bin/bash

cd $(dirname $0)/..
export PROJECT_DIR=$(pwd)
cd - > /dev/null

rm -rf dist *.egg-info
find $PROJECT_DIR -name "*.pyc" | xargs rm
