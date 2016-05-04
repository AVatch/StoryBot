#!/usr/bin/env python
import os
from os.path import join, dirname
from dotenv import load_dotenv
dotenv_path = join(dirname(__file__), './storyBot/.env')
load_dotenv(dotenv_path)

import sys


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "storyBot.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
