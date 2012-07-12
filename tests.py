# encoding=utf-8

from flask import json, url_for

import unittest

from example import app, db


class FlaskTestCase(unittest.TestCase):

    def setUp(self):
        super(FlaskTestCase, self).setUp()
        app.config['DEBUG'] = True
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        db.create_all()
        self.app = app.test_client()

    def request(self, method, url, data=None):
        meth = getattr(self.app, method.lower())
        if data is not None:
            data = json.dumps(data)
        return meth(url, data=data, content_type='application/json')

    def create_workout(self):
        return self.request('post', '/workouts', {'score': 1})

    def test_hal(self):
        # Test validation

        res = self.request('post', '/workouts', {'score': 0})
        self.assertEqual(res.status_code, 422)
        self.assertIn('score', json.loads(res.data)['errors'])

        res = self.create_workout()
        self.assertEqual(res.status_code, 201)

        res = self.request('patch', '/workouts/1', {'score': 4})
        self.assertEqual(res.status_code, 200)

        res = self.request('get', '/workouts')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(json.loads(res.data)['_embedded']['workouts']), 1)

        res = self.request('get', '/workouts/1')
        self.assertEqual(res.status_code, 200)
        self_href = json.loads(res.data)['_links']['self']['href']
        self.assertEqual(self_href, '/workouts/1')

        # Pagination?
        self.create_workout()
        self.create_workout()

        res = self.request('get', '/workouts')
        links = json.loads(res.data)['_links']
        self.assertEqual(links['next']['href'], '/workouts?page=2')

if __name__ == '__main__':
    db.create_all()
    unittest.main()
