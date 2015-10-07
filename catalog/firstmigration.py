from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Category, Item, User

import json
import os


engine = create_engine('sqlite:///items.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()


# Create dummy users
user1 = User(name="John Doe", email="emailjohn@example.com",
             picture='https://upload.wikimedia.org/wikipedia/commons/thumb/5/5f/User_with_smile.svg/2000px-User_with_smile.svg.png')  # noqa
session.add(user1)
session.commit()

user2 = User(name="Jane Doe", email="emailjane@example.com",
             picture='https://upload.wikimedia.org/wikipedia/commons/9/98/User-female.svg')  # noqa
session.add(user2)
session.commit()

root_dir = os.path.dirname(__file__)
data = os.path.join(root_dir, 'data.json')
response = open(data)
json_obj = json.load(response)


for i in json_obj['categories']:
    for j in i['items']:
        newItem = Item(id=j['id'],
                       name=j['name'],
                       description=j['description'],
                       date=j['date'],
                       image=j['image'],
                       category_id=j['category_id'],
                       user_id=j['user_id'])
        session.add(newItem)
        session.commit()
    newCategory = Category(id=i['id'],
                           name=i['name'],
                           image=i['image'],
                           user_id=i['user_id'])
    session.add(newCategory)
    session.commit()
