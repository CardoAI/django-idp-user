#!/bin/bash -e
APP_PATH="idp_user"

export PYTHONPATH=$APP_PATH

pytest
