# encoding=utf-8

from flask import request, url_for, current_app, make_response
from flask.helpers import json
from flask.views import MethodView

from dictshield.document import Document

_error_response_headers = {'Content-Type': 'application/json'}


class FormView(MethodView):
    """
    Validates form API requests. Subclass and add the form fields you wish to
    validate against. PATCH validates partial updates whereas POST validates
    that all required fields are present.

    `fields` is a mapping of exposed field names and dictshield The values are
    instances of `dictshield.fields.BaseField` to validate against.

    """

    fields = {}

    def __init__(self, document=None):
        if document is None:
            cls_name = self.__class__.__name__ + "Document"
            self.document = type(cls_name, (Document, ), self.fields)
        else:
            if not isinstance(document, Document):
                raise TypeError("Form documents must be instances of `dictshield.document.Document`")
            self.document = document

    @property
    def clean(self):
        return self.document.make_ownersafe(request.json)

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
        self.errors = validate(request.json, validate_all=True) or None
        return not bool(self.errors)

    def error_response(self):
        """
        Return a basic application/json response with status code 422 to inform
        the consumer of validation errors in the form request.
        """
        errors = dict([(e.field_name, e.reason) for e in self.errors])  # TODO what about multiple errors per field
        content = json.dumps(dict(message="Validation error", errors=errors))
        return make_response(content, 422, _error_response_headers)

    def dispatch_request(self, *args, **kwargs):
        if not self.validate():
            return self.error_response()
        return super(FormView, self).dispatch_request(*args, **kwargs)

    def schema_response(self):
        """Return a schema+json response for the document. """
        return self.document.to_jsonschema(), 200, {
            'Content-Type': 'application/schema+json',
            'Accept': 'application/json; charset=utf-8'}


class QueryView(MethodView):
    """
    Add `url_kwargs` to the view class instance. The HTTP method class methods
    do *not* receive the args and kwargs from the Route.

    """

    def dispatch_request(self, *args, **kwargs):
        self.url_kwargs = kwargs
        return super(QueryView, self).dispatch_request()


class ResourceView(QueryView):

    content_type = 'application/hal+json'

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
        # find a best match for the subresource URL.
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
            # Avoid n+1 querying by settings `query` to the instance
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

    content_type = 'application/hal+json'

    per_page = 40

    def __init__(self, subresource_endpoint=None):
        self.subresource_endpoint = subresource_endpoint

    @property
    def json(self):
        return {'total': self.page.total, 'per_page': self.page.per_page}

    def query(self):
        raise NotImplementedError()

    def links(self):
        view_name = request.url_rule.endpoint
        _links = {'self': {'href': url_for(view_name)}}
        if self.page.pages > 0:
            if self.page.page == self.page.pages:
                _links['last'] = _links['self']
            else:
                _links['last'] = {'href': url_for(view_name, page=self.page.pages)}
        if self.page.has_next:
            _links['next'] = {'href': url_for(view_name, page=self.page.next_num)}
        if self.page.has_prev:
            _links['previous'] = {'href': url_for(view_name, page=self.page.prev_num)}
        return _links

    def embedded(self):
        endpoint = self.subresource_endpoint
        if endpoint is None:
            get_json = lambda o: o.json
        else:
            resource = current_app.view_functions[endpoint].view_class
            get_json = lambda o: resource.as_resource(endpoint, o).json
        return [get_json(item) for item in self.page.items]

    def get(self):
        page_num = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', self.per_page))
        per_page = min(per_page, self.per_page)  # Upper limit
        self.page = self.query().paginate(page_num, per_page=per_page)
        content = json.dumps(dict(
            _embedded={request.url_rule.endpoint: self.embedded()},
            _links=self.links(), **self.json))
        return content, 200, {'Content-Type': self.content_type}
