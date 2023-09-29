#!/bin/bash -e

APP_PATH="idp_user"

ruff $APP_PATH --fix
black $APP_PATH
