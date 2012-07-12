# encoding=utf-8

import datetime

from flask import Flask, make_response
from dictshield.fields import IntField
from flask_sqlalchemy import SQLAlchemy
from flask_hal import FormView, IndexView, ResourceView


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
db = SQLAlchemy(app)


class Workout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer, index=True)
    created = db.Column(db.DateTime, default=datetime.datetime.now)

    @property
    def json(self):
        return dict(id=self.id, score=str(self.score))


class WorkoutResource(ResourceView):
    def query(self):
        return Workout.query.get_or_404(self.url_kwargs['id'])


class WorkoutIndex(IndexView):

    per_page = 2

    def query(self):
        return Workout.query.order_by(Workout.created.desc())


class WorkoutForm(FormView):

    fields = {
        "score": IntField(required=True, min_value=1),
    }

    def patch(self, id):
        workout = Workout.query.get_or_404(id)
        for k, v in self.clean.iteritems():
            setattr(workout, k, v)
        db.session.add(workout)
        resource = WorkoutResource.as_resource('workout', workout)
        response = make_response(resource.get())
        return response, 200, {'Location': resource.url}

    def post(self):
        workout = Workout(**self.clean)
        db.session.add(workout)
        db.session.commit()
        resource = WorkoutResource.as_resource('workout', workout)
        response = make_response(resource.get())
        return response, 201, {'Location': resource.url}


workout_resource = WorkoutResource.as_view('workout')
workout_form = WorkoutForm.as_view('workout_form')
workout_index = WorkoutIndex.as_view('workouts', subresource_endpoint='workout')

app.add_url_rule('/workouts', view_func=workout_index, methods=['GET'])
app.add_url_rule('/workouts', view_func=workout_form, methods=['POST'])
app.add_url_rule('/workouts/<int:id>', view_func=workout_resource, methods=['GET'])
app.add_url_rule('/workouts/<int:id>', view_func=workout_form, methods=['PATCH'])

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
