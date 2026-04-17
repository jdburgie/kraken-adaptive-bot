#!/bin/bash

export $(cat .env | xargs)
python3 -m bot.main