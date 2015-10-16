#!/usr/bin/env python
"""
project.py -- Bucketlist Catalog for Udacity Full Stack Web Dev Nanodegree

The classes used are the User, Category and Item.
Items belongs to one Category but one Category can have many items.
The deletion of categories imply the deletion of their children items.

created by Anne-Sophie Sept 2015

"""
APPLICATION_NAME = "Catalog"

# setup flask
from flask import Flask

app = Flask(__name__, static_folder='static', static_url_path='')
# Access to the configuration variables via app.config["VAR_NAME"]
app.config.from_object('config')
app.config.from_pyfile('../config.py')

import catalog.views


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True

__author__ = 'aslebloas@gmail.com (Anne-Sophie Le Bloas)'
