import logging
import errors
import forms
from urllib2 import Request, HTTPError
from rtkit.parser import RTParser

class RTObj:
    """RT Simple Object Container
    
    .. doctest::
    
        resource = RTResource('http://rt.example.com/REST/1.0/', 'webmaster', 'secret', CookieAuthenticator)
        try:
            response = resource.get(path='ticket/28')
            myTicket = response.as_object()
            
        except RTResourceError as e:
            logger.error(e.response.status_int)
            logger.error(e.response.status)
            logger.error(e.response.parsed)

        ## Show Stuff
        print myTicket.Subject, myTicket.id
        print myTicket.get_custom("my_custom")
        print myTicket.keys()  # list of keys
        print mtTicket.as_dict() # return as dict and key/value pair

        ## Update Stuff
        myTicket.set_custom("my_custom", "New Val")
        myTicker.Subject = myTicket.Subject + " my Xtra"
    """
    
    def __init__(self ,dic=None):
        """
        :param dic; The dictionary to make Oo"""
        if dic:
            self.__dict__ =  dic
        
    def keys(self):
        """:return: A list with strings of the field names"""
        return sorted(self.__dict__.keys())
    
    def get(self, name):
        """This is useful as some "keys" are not ooable eg ob.get("X-yx");
           
        :param name: The value to get
        :return: The value of name."""
        return self.__dict__[name]
    
    def as_dict(self):
        """
        :return: Dictionary of data as key value pairs"""
        return self.__dict__


    def get_custom(self, name):
        """Get a custom field, a short cut to CF.{name}

        :param name: of custom field eg 'Works Order' 
        :return: the data as string 
        """
        return self.__dict__["CF.{%s}" % name]

    def set_custom(self, name, val):
        """Set a custom field, a short cut to CF.{name}

        :param name: of custom field eg 'Works Order' 
        :param val: New value to set to
        """
        self.__dict__["CF.{%s}" % name] = val
        
    def __repr__(self):
        return '<RtObj %s>' % (self.id)

class RTResource(object):
    """REST Resource Object"""
    def __init__(self, url, username, password, auth, **kwargs):
        """Create Connection Object

        :param url: Server URL
        :param username: RT Login
        :param password: Password
        :param auth: Instance of :py:mod:`rtkit.authenticators`
        """
        self.auth = auth(username, password, url)
        self.response_cls = kwargs.get('response_class', RTResponse)
        self.logger = logging.getLogger('rtkit')

    def get(self, path=None, headers=None):
        """GET from the server"""
        return self.request('GET', path, headers=headers)

    def post(self, path=None, payload=None, headers=None):
        """POST to the server"""
        return self.request('POST', path, payload, headers)

    def request(self, method, path=None, payload=None, headers=None):
        """Make request to server"""
        headers = headers or dict()
        headers.setdefault('Accept', 'text/plain')
        if payload:
            payload = forms.encode(payload, headers)
        self.logger.debug('{0} {1}'.format(method, path))
        self.logger.debug(headers)
        self.logger.debug('%r' % payload)
        req = Request(
            url=self.auth.url + path,
            data=payload,
            headers=headers,
        )
        try:
            response = self.auth.open(req)
        except HTTPError as e:
            response = e
        return self.response_cls(req, response)


class RTResponse(object):
    """Represents the REST response from server"""
    def __init__(self, request, response):
        self.headers = response.headers
        """Headers as dict"""

        self.body = response.read()
        """Request Body"""

        self.status_int = response.code
        """Status Code"""

        self.status = '{0} {1}'.format(response.code, response.msg)
        """Status String"""

        self.logger = logging.getLogger('rtkit')
        """Logger"""

        self.logger.info(request.get_method())
        self.logger.info(request.get_full_url())
        self.logger.debug('HTTP_STATUS: {0}'.format(self.status))
        r = RTParser.HEADER.match(self.body)
        if r:
            self.status = r.group('s')
            self.status_int = int(r.group('i'))
        else:
            self.logger.error('"{0}" is not valid'.format(self.body))
            self.status = self.body
            self.status_int = 500
        self.logger.debug('%r' % self.body)

        self.parsed = None
        """A List of Tuples of  data"""
        try:
            decoder = RTParser.decode
            if self.status_int == 409:
                decoder = RTParser.decode_comment
            self.parsed = RTParser.parse(self.body, decoder)
        except errors.RTResourceError as e:
            self.parsed = []
            self.status_int = e.status_int
            self.status = '{0} {1}'.format(e.status_int, e.msg)
        self.logger.debug('RESOURCE_STATUS: {0}'.format(self.status))
        self.logger.info(self.parsed)

    def as_dict(self):
        """:return: dict with the data"""
        d = {}
        for p in self.parsed[0]:
            d[p[0]] = p[1]
        return d
        
    def as_object(self):
        """:return: A :py:class:`rtkit.resource.RtObj` with data as attributes"""
        ob = RTObj(self.as_dict())
        return ob
        