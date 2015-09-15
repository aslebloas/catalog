# Catalog - Bucketlist
## Synopsis

This Catalog Bucketlist is a web application which enables the users to browse some lifetime goals and add their owns.
Unlogged users can browse categories and goals, but they need to be logged in to create new ones and they must be their creators to edit and delete them.
Sign in 

## Folder Structure

* Static
  * css
    * custom.css
* templates
  * base.html
  * categories.html
  * deleteCategory.html
  * deleteItem.html
  * editCategory.html
  * editItem.html
  * item.html
  * items.html
  * login.html
  * navbar.html
  * newCategory.html
  * newItem.html
* client_secrets.json
* database_setup.py
* fb_client_secrets.json
* project.py
* README.md


## Motivation

This Catalog Bucketlist website has been created as a project for Udacity Full Stack Developer Nanodegree.


## Further Development
I have created it as standard as possible so it can be easily reused.
As a consequence, they are 3 tables in the database: User, Category and Item.
Item correspond here to goals, but if you modify the front-end, it can be anything (gifts, books). It's the same for categories which you can change to people or places in the front-end.


## Installation

Python is required.
Bleach is required.
PostgreSQL is required.
Flask is required.
sqlalchemy is required.
flask-seasurf is required.

To get started:

git clone git://github.com/aslebloas/bucketlist-catalog.git
cd catalog
python project.py
Access and test your application by visiting http://localhost:8000 locally

## API Endpoints
I have created a JSON APIs to view Categories and Items information.
It is available at '/catalog/JSON'

## License

Open Source
