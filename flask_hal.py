# encoding=utf-8

from flask import jsonify, request, url_for, current_app
from flask.helpers import json
from flask.exceptions import JSONBadRequest, JSONHTTPException
from flask.views import MethodView

from dictshield.document import Document


class UnprocessableJSONRequest(JSONHTTPException):

    code = 422

    def get_body(self, environ):
        errors = self.get_description(environ)
        return json.dumps(dict(errors=errors))


class FormView(MethodView):
    """
    Validate the submission of new resources or updates to existing resources.
    Subclass and add the form fields you wish to validate against. PATCH can
    validate partial updates as it should.

    """

    methods = ['POST', 'PATCH']

    fields = {}

    @property
    def document(self):
        cls = type(self.__class__.__name__ + "Document", (Document, ), self.fields)
        return cls(**request.json)

    @property
    def clean(self):
        filtered = self.document.to_python()  # Still includes dictshield internals
        return self.document.make_json_ownersafe(filtered, encode=False)

    def validate(self):
        """
        Sets an error attribute with a `field_name`: message dictionary.
        Returns `True` if valid and `False` if `errors` is non-empty.
        """
        if request.method == "PATCH":
            # Allow partial documents when PATCH’ing
            validate = self.document.validate_class_partial
        else:
            validate = self.document.validate_class_fields
        self.errors = validate(request.json.copy(), validate_all=True) or None
        return not bool(self.errors)

    def error_response(self):
        errors = dict([(e.field_name, e.reason) for e in self.errors])
        raise UnprocessableJSONRequest(errors)

    def dispatch_request(self, *args, **kwargs):
        if not request.json:
            raise JSONBadRequest()
        if not self.validate():
            return self.error_response()
        return super(FormView, self).dispatch_request(*args, **kwargs)

    def options(self):
        """Inform client that PATCH documents should be utf-8 JSON. """
        return None, 200, {
            'Accept-Patch': 'application/json;charset=utf-8',
            'Allow': ', '.join(self.methods)}


class QueryView(MethodView):
    """
    Add `url_kwargs` to the view class instance.
     The
    endpoint name is what the resource name will be exposed as to the API
    consumer. See "workouts":

    {
      "_embedded": {
        "workouts": [{
            "score": 220
        }, ... ]
    }

    """

    def dispatch_request(self, *args, **kwargs):
        self.url_kwargs = kwargs
        return super(QueryView, self).dispatch_request()


class ResourceView(QueryView):

    methods = ['GET']
    content_type = 'application/hal+json'

    @property
    def query(self):
        return self.query().filter_by(**self.url_kwargs).first_or_404()

    def get_url(self):
        if hasattr(self, "url"):
            return self.url
        return request.path

    def links(self):
        links = {'self': {'href': self.get_url()}}
        if callable(getattr(self.query(), "links", None)):
            links.update(self.query().links())
        return links

    @property
    def json(self):
        return dict(_links=self.links(), **self.query().json)

    def get(self):
        return json.dumps(self.json), 200, {'Content-Type': self.content_type}

    @classmethod
    def as_resource(cls, endpoint, model_instance=None):
        # Instantiate from endpoint and object. Traverse the app url_map and
        # finds a best match for the subresource URL.
        def get_url_kwargs():
            for rule in current_app.url_map._rules_by_endpoint[endpoint]:
                if 'GET' in rule.methods and rule.arguments:
                    for arg in rule.arguments:
                        if hasattr(model_instance, arg):
                            yield arg, getattr(model_instance, arg)
                    raise StopIteration()
        self = cls()
        self.url_kwargs = dict(get_url_kwargs())
        self.url = url_for(endpoint, **self.url_kwargs)
        if model_instance is not None:
            # Avoid n+1 querying
            self.query = lambda: model_instance
        return self


class IndexView(QueryView):
    """
    Paginated resources. Uses `?page=<int>` URL argument. Route this view like
    so:

        workout_resource = ResourceView.as_view(Workout, 'workout')
        workout_index = IndexView.as_view(Workout, 'workouts', resource=workout_resource)

        app.add_url_rule('/workouts/<int:id>', workout_resource, methods=['GET'])
        app.add_url_rule('/workouts', workout_index, methods=['GET'])

    Notice that a `workout_resource` was created first. This is cleaner since
    HAL embeds subresources and we can generate a HAL compliant structure for
    this index.

    It might be a good idea to order to `query` to get predictable results.

    """

    methods = ['GET']
    content_type = 'application/hal+json'

    per_page = 40

    def __init__(self, subresource_endpoint=None):
        if subresource_endpoint is None:
            raise TypeError("IndexView must be instantiated with a resource instance. ex: "
                            "`IndexView.as_view(Model, 'things', subresource_endpoint='thing')`")
        self.subresource_endpoint = subresource_endpoint

    @property
    def json(self):
        return {}

    def query(self):
        raise NotImplementedError()

    def links(self):
        page = self.build_page()
        view_name = request.url_rule.endpoint
        _links = {'self': url_for(view_name)}
        if hasattr(self, "template"):
            _links['find'] = {'href': self.template, "templated": True}
        if page.pages > 0:
            _links['last'] = {'href': url_for(view_name, page=page.pages)}
        if page.has_next:
            _links['next'] = {'href': url_for(view_name, page=page.next_num)}
        if page.has_prev:
            _links['previous'] = {'href': url_for(view_name, page=page.previous_num)}
        return _links

    def embedded(self):
        endpoint = self.subresource_endpoint
        subresource = current_app.view_functions[endpoint].view_class
        return [subresource.as_resource(endpoint, item).json \
            for item in self.build_page().items]

    def build_page(self):
        page_num = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', self.per_page))
        per_page = min(per_page, self.per_page)  # Upper limit
        return self.query().paginate(page_num, per_page=per_page)

    def get(self):
        links = self.links()
        embedded = self.embedded()
        response = jsonify(_embedded={request.url_rule.endpoint: embedded},
                           _links=links, **self.json)
        return response, 200, {'Content-Type': self.content_type}
