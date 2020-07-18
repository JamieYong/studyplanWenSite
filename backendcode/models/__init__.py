import json

import peewee as pw
import sys
from aistore_config import aistore_configs
from src.util import Util
from playhouse.pool import PooledMySQLDatabase

utilClass = Util()


dbconn = pw.MySQLDatabase("test", host=aistore_configs['db_host'], port=3306, user=aistore_configs["db_user"], passwd=aistore_configs["db_pass"])

class JSONField(pw.TextField):
    def db_value(self, value):
        return json.dumps(value)

    def python_value(self, value):
        if value is not None:
            return json.loads(value)

class MySQLModel(pw.Model):
    """A base model that will use our MySQL database"""
    class Meta:
        database = dbconn

class usersTable(MySQLModel):
    class Meta:
        db_table = 'users'

    id = pw.IntegerField()
    email = pw.CharField()
    password = pw.CharField()
    resetPasswordToken = pw.CharField()
    confirmed = pw.IntegerField()
    firstname = pw.CharField()
    name = pw.CharField()
    resetPasswordRequestDatetime = pw.DateTimeField()
    resetPasswordVerifyLink = pw.CharField()
    resetPasswordVerifyTokenID = pw.CharField()
    emailVerifyRequestDatetime = pw.CharField()
    emailVerifyDatetime = pw.CharField()
    emailVerifyTokenID = pw.CharField()
    emailVerifyLink = pw.CharField()
    emailChangeValue = pw.CharField()
    emailChangeRequestDatetime = pw.CharField()
    emailChangeVerifyLink = pw.CharField()
    emailChangeVerifyTokenID = pw.CharField()
    created_at = pw.DateTimeField()
    updated_at = pw.DateTimeField()
    emailVerifiedYN = pw.CharField()
    emailTokenCode = pw.CharField()
    token = pw.TextField()
    gender = pw.CharField()
    appTokenCode = pw.CharField()
    appTokenCodeUpdatedAt = pw.DateTimeField()