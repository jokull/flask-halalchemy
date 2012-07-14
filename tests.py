# encoding=utf-8

from flask import json

import unittest

from test_example import app, db


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

    def create_workout(self, score=1):
        return self.request('post', '/workouts', {'score': score})

    def href(self, hal):
        return hal['_links']['self']['href']

    def test_resource(self):
        # Test validation

        res = self.create_workout(score=0)  # Bad score
        self.assertEqual(res.status_code, 422)
        self.assertIn('score', json.loads(res.data)['errors'])
        self.assertEqual(res.headers['content-type'], 'application/json')

        res = self.create_workout()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.headers['content-type'], 'application/hal+json')
        workout_1 = json.loads(res.data)
        workout_2 = json.loads(self.create_workout().data)

        res = self.request('patch', self.href(workout_1), {'score': 0})
        self.assertEqual(res.status_code, 422)
        self.assertIn('score', json.loads(res.data)['errors'])

        res = self.request('patch', self.href(workout_1), {'score': 4})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers['content-type'], 'application/hal+json')

        res = self.request('patch', self.href(workout_1), {'title': 'Fight Gone Bad'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers['content-type'], 'application/hal+json')
        title = json.loads(res.data)['title']
        self.assertEqual(title, u"Fight Gone Bad")
        self.assertIsInstance(title, unicode)

        res = self.request('get', self.href(workout_1))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers['content-type'], 'application/hal+json')

        # PATCH before worked
        self.assertEqual(json.loads(res.data)['score'], 4, "PATCH should have updated the score")

        res = self.request('get', '/workouts')
        self.assertEqual(res.status_code, 200)
        workouts = json.loads(res.data)['_embedded']['workouts']
        self.assertEqual(len(workouts), 2)

        # First workout should be the last in index
        self.assertEqual(workouts[0]['id'], workout_2['id'])
        self.assertEqual(workouts[1]['id'], workout_1['id'])

        links = json.loads(res.data)['_links']
        self.assertNotIn('next', links, u"")

        # Per Page is set to 2 so creating more workouts should make new pages
        self.create_workout()
        self.create_workout()

        res = self.request('get', '/workouts')
        links = json.loads(res.data)['_links']
        self.assertIn('next', links, u"With per_page set to 2, this resource should be split and point to the next page")

        res = self.request('get', links['next']['href'])
        self.assertEqual(res.status_code, 200)
        links = json.loads(res.data)['_links']
        self.assertNotIn('next', links, u"Last page should not have `next` link")

        res = self.request('get', '/workouts?per_page=4')
        links = json.loads(res.data)['_links']
        self.assertIn('next', links, u"per_page was overwritten in a url argument "
                                     u"but and server seems to have respected it "
                                     u"since a next link was introduced in the _links. "
                                     u"However the upper limit should be the `per_page`"
                                     u"set on the class.")


if __name__ == '__main__':
    db.create_all()
    unittest.main()
