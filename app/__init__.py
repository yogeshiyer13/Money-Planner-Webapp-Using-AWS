'''
Creates flask instance

'''
from flask import Flask
from flask_googlecharts import GoogleCharts

import os
webapp = Flask(__name__)
charts = GoogleCharts(webapp)
webapp.secret_key = os.urandom(20)

from app import main
from app import users
from app import images
