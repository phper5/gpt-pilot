from peewee import ForeignKeyField, CharField
from peewee import TextField
from database.models.components.base_models import BaseModel
from database.models.user import User
from database.config import DATABASE_TYPE
from database.models.components.sqlite_middlewares import JSONField
from playhouse.postgres_ext import BinaryJSONField


class Project(BaseModel):
    user = ForeignKeyField(User, backref='projects')
    name = CharField(null=True)
    description = TextField()
    step = CharField()
    app_type = CharField()

    if DATABASE_TYPE == 'postgres':
        app_data = BinaryJSONField()
        data = BinaryJSONField(null=True)
    else:
        app_data = JSONField()
        data = JSONField(null=True)