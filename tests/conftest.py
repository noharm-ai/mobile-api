import pytest, json
from mobile import app
from models.main import User
from unittest.mock import patch
from flask_jwt_extended import (create_access_token)
from models.appendix import Memory

import sys
sys.path.append('..')

from config import Config
import sqlalchemy
from sqlalchemy.orm import sessionmaker

engine = sqlalchemy.create_engine(Config.POTGRESQL_CONNECTION_STRING)
DBSession = sessionmaker(bind=engine)
session = DBSession()
session.connection(execution_options={'schema_translate_map': {None: 'demo'}})

with app.test_request_context():
	access_token = create_access_token('1')

def make_headers(jwt):
    return {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': 'Bearer {}'.format(jwt)
            }

def user_find(id):
	user = User()
	user.schema = "demo"
	return user

def setSchema(schema):
	return schema

def session_commit():
    session.commit()
    session.connection(execution_options={'schema_translate_map': {None: 'demo'}})

@pytest.fixture
def client():
    client = app.test_client()
    yield client

def get_access(client, email='demo', password='demo', roles = ["suporte"]):
    mimetype = 'application/json'
    headers = {
        'Content-Type': mimetype,
        'Accept': mimetype
    }
    data = {
        "email": email,
        "password": password
    }
    url = '/authenticate'
    
    update_roles(email, roles)

    response = client.post(url, data=json.dumps(data), headers=headers)
    my_json = response.data.decode('utf8').replace("'", '"')
    data_response = json.loads(my_json)
    access_token = data_response['access_token']
    return access_token

def update_roles(email, roles):

    user = session.query(User).filter_by(email = email).first()
    if user != None:
        user.config = {"roles":roles}
        session_commit()

    # mem.kind = mem_kind
    # mem.value = mem_value
    # mem.update = datetime.today()
    # mem.user = 0
    # def delete_memory(key):
    # memory = session.query(Memory).get(key)
    # if memory:
    #     session.delete(memory)
    #     session_commit()ion_commit()
    # return mem.key


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    test_fn = item.obj
    docstring = getattr(test_fn, '__doc__')
    if docstring:
        report.nodeid = docstring
