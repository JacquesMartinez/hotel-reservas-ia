import sys
import types
from unittest.mock import MagicMock

import pytest

#the real db package connects to MySQL on import; the tests replace it with a mock
fake_db = types.ModuleType('db')
fake_db.mysqldb = MagicMock()
sys.modules['db'] = fake_db

import api
import serve


@pytest.fixture
def mysqldb(monkeypatch):
	mock = MagicMock()
	monkeypatch.setattr(api.db, 'mysqldb', mock)
	return mock


@pytest.fixture
def client():
	serve.app.config['TESTING'] = True
	return serve.app.test_client()
