import sys
from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
Base = declarative_base()


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    email = Column(String(80), nullable=False)
    picture = Column(String(250))


class Category(Base):
    __tablename__ = 'category'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    image = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
    items = relationship("Item", cascade="all,delete", backref="category")

    @property
    def serialize(self):
        # Returns objec data in easily serializeable format
        return {
            'id': self.id,
            'name': self.name,
            'user_id': self.user_id,
            'items': [item.serialize for item in self.items]
        }

    def serializeToXml(self, content):
        content.append("<Category>")
        content.append("<ID>%s</ID>" % self.id)
        content.append("<Name>%s</Name>" % self.name)
        content.append("<ImageUrl>%s</ImageUrl>" % self.image)

        if self.items:
            content.append("<Item>")
            for item in self.items:
                item.serializeToXml(content)
            content.append("</Item>")

        content.append("</Category>")


class Item(Base):
    __tablename__ = 'item'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    description = Column(Text, nullable=True)
    date = Column(String(8), nullable=False)
    image = Column(Text, nullable=False)
    category_id = Column(Integer, ForeignKey('category.id'))
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        # Returns objec data in easily serializeable format
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'date': self.date,
            'image': self.image,
            'category_id': self.category_id,
            'user_id': self.user_id,
        }

    def serializeToXml(self, content):
        content.append("<Item>")
        content.append("<ID>%s</ID>" % self.id)
        content.append("<Name>%s</Name>" % self.name)
        content.append("<Description>%s</Description>" % self.description)
        content.append("<Date>%s</Date>" % self.date)
        content.append("<ImageUrl>%s</ImageUrl>" % self.image)
        content.append("</Item>")

# insert at end of file
engine = create_engine('postgresql://catalog:udacity@localhost/items')

Base.metadata.create_all(engine)
