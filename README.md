flask_hal.py
============

Expose SQLAlchemy model instances and paginated querysets as **hal+json**
resources. Warning: Don’t fall in love with this idea. It is only meant to
quickly expose a `Model` and supply hooks to validate incoming data. Generally
speaking you should aim to expose processes not just map CRUD SQL operations
to the HTTP verbs. That being said, I believe this is a common enough scenario
to automate.

I have made an effort not to tie it too deeply into SQLAlchemy so it would be
easy to adopt other database storages. The biggest blocker is the
Flask-SQLAlchemy pagination class.

Three Flask class based views are provided:

 + `ResourceView`: A hal+json resource for Model instances
 + `IndexView`: A paginated hal+json resource for Model querysets
 + `FormView`: Validates incoming JSON data, reports errors nicely (POSTs to
               indexes and PATCHes resources)

The following assumptions are made:

 + `get_query` returns a result set for `IndexView` and a SQLAlchemy `Query`
   instance for `ResourceView`.
 + Models have a `json` attribute that exposes publically available fields
   and their values. This is what what your API consumer sees.
 + You are ok with using dictshield fields and validation :)

The GET method is already implemented for `ResourceView` and `IndexView`
resources.

See `example.py` for ... an example.

About HAL
---------

See the [Internet Draft](http://tools.ietf.org/html/draft-kelly-json-hal-03)

Paginated Hypermedia API Language (HAL) response example:

    HTTP/1.0 200 OK
    Content-Type: application/hal+json
    Content-Length: 283
    Server: Werkzeug/0.8.3 Python/2.7.2
    Date: Thu, 12 Jul 2012 18:26:33 GMT
    {
      "_embedded": {
        "workouts": [
          {
            "_links": {
              "self": {
                "href": "/workouts/1"
              }
            }
            "id": 1,
            "score": "1",
          },
          {
            "_links": {
              "self": {
                "href": "/workouts/2"
              }
            }
            "id": 2,
            "score": "1",
          }
        ]
      },
      "_links": {
        "self": {
          "href": "/workouts"
        },
        "last": {
          "href": "/workouts?page=3"
        },
        "next": {
          "href": "/workouts?page=2"
        }
      }
    }
