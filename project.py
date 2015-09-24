import bleach
import os

from database_setup import Base, Category, Item, User
from flask import Flask, flash, jsonify
from flask import redirect, render_template, request, url_for, make_response
from flask import send_from_directory
from flask import session as login_session
from flask.ext.seasurf import SeaSurf
from functools import wraps
from oauth2client.client import flow_from_clientsecrets, FlowExchangeError
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from werkzeug import secure_filename

import httplib2
import json
import random
import requests
import string

app = Flask(__name__)

# FILE UPLOAD
UPLOAD_FOLDER = 'UPLOAD_FOLDER/'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024

# Cross-site request forgery prevention
csrf = SeaSurf(app)

# JSON
CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']


APPLICATION_NAME = "Catalog"

# Connect to Database and create database session
engine = create_engine('sqlite:///items.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


# File uploads
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


# facebook login
@csrf.exempt
@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    ''' Exempted from CSRF validation.'''
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token

    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (  # noqa
        app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.4/me"
    # strip expire tag from access token
    token = result.split("&")[0]

    url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    """ The token must be stored in the login_session in order to properly logout,
    let's strip out the information before the equals sign in our token """
    stored_token = token.split("=")[1]
    login_session['access_token'] = stored_token

    # Get user picture
    url = 'https://graph.facebook.com/v2.4/me/picture?%s&redirect=0&height=200&width=200' % token  # noqa
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '  # noqa

    flash("Now logged in as %s" % login_session['username'])
    return output


# facebook logout
@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (
        facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "function myFunction() {alert('You have been successfully logged out'); window.location.href = '/';}</script><body onload='myFunction()'>"  # noqa


# google login
@csrf.exempt
@app.route('/gconnect', methods=['POST'])
def gconnect():
    ''' Exempted from CSRF validation.'''
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data
    print "code received %s " % code

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials.to_json()
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '  # noqa
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


# User Helper Functions
def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# Google logout - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] != '200':
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['credentials']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showCategories'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showCategories'))


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in login_session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# show all categories
@app.route('/')
@app.route('/catalog/')
def showCategories():
    categories = session.query(Category).order_by(asc(Category.name)).all()
    items = session.query(Item).all()
    return render_template('categories.html',
                           categories=categories,
                           items=items)


# Create New Category for logged in user otherwise redirect to login page
@app.route('/catalog/new', methods=['GET', 'POST'])
@login_required
def newCategory():
    if request.method == 'POST':
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        newCategory = Category(
            name=bleach.clean(request.form['name']),
            image=url_for('uploaded_file', filename=filename),
            user_id=login_session['user_id'])
        session.add(newCategory)
        flash('New Category successfully added!')
        session.commit()
        return redirect(url_for('showCategories'))
    return render_template('newCategory.html')


# Edit Category
@app.route('/catalog/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
def editCategory(category_id):
    editedCategory = session.query(Category).filter_by(id=category_id).one()
    if request.method == 'POST':
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        if request.form['name']:
            editedCategory.name = bleach.clean(request.form['name'])
        if request.form['image']:
            editedCategory.image = url_for('uploaded_file', filename=filename)
        session.add(editedCategory)
        flash('Category successfully edited')
        session.commit()
        return redirect(url_for('showCategories'))
    return render_template('editCategory.html', category=editedCategory)


# Delete Category
@app.route('/catalog/<int:category_id>/delete', methods=['GET', 'POST'])
@login_required
def deleteCategory(category_id):
    categoryToDelete = session.query(Category).filter_by(id=category_id).one()
    itemsToDelete = session.query(Item).filter_by(
        category_id=category_id).all()
    if categoryToDelete.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to delete this category.'); window.location.href = '/';}</script><body onload='myFunction()'>"  # noqa
    if request.method == 'POST':
        session.delete(categoryToDelete)
        session.delete(itemsToDelete)
        flash('%s successfully deleted!' % categoryToDelete.name)
        session.commit()
        return redirect(url_for('showCategories'))
    return render_template('deleteCategory.html', category=categoryToDelete)


# Show all items from a category
@app.route('/catalog/<int:category_id>/items')
def showItems(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    creator = getUserInfo(category.user_id)
    items = session.query(Item).filter_by(category_id=category_id).all()
    return render_template('items.html',
                           category=category,
                           items=items,
                           creator=creator)


# Show all items from a category
@app.route('/catalog/<int:category_id>/<int:item_id>')
def showItem(category_id, item_id):
    category = session.query(Category).filter_by(id=category_id).one()
    item = session.query(Item).filter_by(id=item_id).one()
    return render_template('item.html',
                           category_id=category_id,
                           category=category,
                           item=item)


# Create an item from a category
@app.route('/catalog/<int:category_id>/items/new', methods=['GET', 'POST'])
@login_required
def newItem(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    if request.method == 'POST':
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        newItem = Item(name=bleach.clean(request.form['name']),
                       description=bleach.clean(request.form['description']),
                       date=bleach.clean(request.form['date']),
                       image=url_for('uploaded_file', filename=filename),
                       category_id=category_id,
                       user_id=login_session['user_id'],)
        session.add(newItem)
        flash('New Item successfully added in %s!' % category.name)
        session.commit()
        return redirect(url_for('showItems', category_id=category_id))
    return render_template('newItem.html')


# Edit an item from a category
@app.route('/catalog/<int:category_id>/<int:item_id>/edit',
           methods=['GET', 'POST'])
@login_required
def editItem(category_id, item_id):
    category = session.query(Category).filter_by(id=category_id).one()
    editedItem = session.query(Item).filter_by(id=item_id).one()
    if request.method == 'POST':
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            editedItem.image = url_for('uploaded_file', filename=filename)
        if request.form['name']:
            editedItem.name = bleach.clean(request.form['name'])
        if request.form['description']:
            editedItem.description = bleach.clean(request.form['description'])
        if request.form['date']:
            editedItem.date = bleach.clean(request.form['date'])
        session.add(editedItem)
        flash('Item successfully edited!')
        session.commit()
        return redirect(url_for('showItems', category_id=category_id))
    return render_template('editItem.html',
                           item=editedItem,
                           category_id=category_id)


# Delete an item from a category
@app.route('/catalog/<int:category_id>/<int:item_id>/delete',
           methods=['GET', 'POST'])
@login_required
def deleteItem(category_id, item_id):
    category = session.query(Category).filter_by(id=category_id).one()
    itemToDelete = session.query(Item).filter_by(id=item_id).one()
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('%s successfully deleted!' % itemToDelete.name)
        return redirect(url_for('showItems', category_id=category_id))
    return render_template('deleteItem.html', item=itemToDelete)


# JSON API to view Categories and Items information
@app.route('/catalog/JSON')
def catalogJSON():
    categories = session.query(Category).all()
    serializedCategories = []
    for c in categories:
        nextCategory = c.serialize
        items = session.query(Item).filter_by(category_id=c.id).all()
        serializedItems = []
        for i in items:
            serializedItems.append(i.serialize)
        nextCategory['items'] = serializedItems
        serializedCategories.append(nextCategory)
    return jsonify(categories=[serializedCategories])


# XML API to view Categories and Items information
@app.route('/catalog/XML')
def catalogXML():
    """Returns the catalog as XML document."""
    content = []
    content.append("<Categories>")

    categories = session.query(Category).all()
    for category in categories:
        category.serializeToXml(content)
    content.append("</Categories>")

    return str.join("\n", content), 200, {'Content-Type': 'text/xml'}

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
