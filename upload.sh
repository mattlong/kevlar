#!/bin/bash

./clean.sh
python setup.py sdist upload

#pip uninstall $PACKAGE_NAME
#rm -rf ~/.virtualenvs/$PACKAGE_NAME-dev/build/$PACKAGE_NAME
#pip install $PACKAGE_NAME
