#!/usr/bin/env python
#
# Copyright@Share2create License.
#
# Author: Senthilkumar
# Date : 7-Feb-2014
# Release : Initial

"""The project OnScreen.

OnScreen a web application enables the smatter way to
access the web. You can visit all your webpages on signle
screen. no need of openening so tabs in your browser.
"""

__author__ = 'sentenwin@google.com (Senthilkumar M)'


import httplib2
import logging
import os
import pickle
import webapp2
import jinja2

from apiclient import discovery
from oauth2client import appengine
from oauth2client import client
from google.appengine.api import memcache
from google.appengine.api import users
from datetime import datetime
from google.appengine.ext import db



from models import Notes

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
jinja_environment = \
    jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_DIR))

# CLIENT_SECRETS, name of a file containing the OAuth 2.0 information for this
# application, including client_id and client_secret, which are found
# on the API Access tab on the Google APIs
# Console <http://code.google.com/apis/console>
CLIENT_SECRETS = os.path.join(os.path.dirname(__file__), 'client_secrets.json')

# Helpful message to display in the browser if the CLIENT_SECRETS file
# is missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
<h1>Warning: Please configure OAuth 2.0</h1>
<p>
To make this sample run you will need to populate the client_secrets.json file
found at:
</p>
<p>
<code>%s</code>.
</p>
<p>with information found on the <a
href="https://code.google.com/apis/console">APIs Console</a>.
</p>
""" % CLIENT_SECRETS


http = httplib2.Http(memcache)
service = discovery.build("plus", "v1", http=http)
decorator = appengine.oauth2decorator_from_clientsecrets(
    CLIENT_SECRETS,
    scope='https://www.googleapis.com/auth/plus.me',
    message=MISSING_CLIENT_SECRETS_MESSAGE)

class BaseHandler(webapp2.RequestHandler):

    @webapp2.cached_property
    def jinja2(self):
        return jinja2.get_jinja2(app=self.app)

    def render_template(
        self,
        filename,
        template_values,
        **template_args
        ):
        template = jinja_environment.get_template(filename)
        self.response.out.write(template.render(template_values))


class MainHandler(BaseHandler):

	@decorator.oauth_aware
	def get(self):
		user = users.get_current_user()
		if user:
			notes = Notes.all().filter("id =", user.user_id())
			if decorator.has_credentials():
				try:
					http = decorator.http()
					gplus = service.people().get(userId='me').execute(http=http)
					self.render_template('index.html', {'notes': notes, 'gplus': gplus, 'users': users})
				except client.AccessTokenRefreshError:
					self.redirect('/')
			else:
				self.redirect(decorator.authorize_url())
		else:
			self.redirect(users.create_login_url(self.request.uri))


class CreateNote(BaseHandler):

    def post(self):
		user = users.get_current_user()
		if user:
			n = Notes(id=user.user_id(),
						author=self.request.get('author'),
						text=self.request.get('text'),
						priority=self.request.get('priority'),
						status=self.request.get('status'))
			n.put()
			return webapp2.redirect('/')
		else:
			self.redirect('/')


    def get(self):
		user = users.get_current_user()
		if user:
			self.render_template('create.html', {'users': users})
		else:
			self.redirect(users.create_login_url(self.request.uri))
		

class EditNote(BaseHandler):

    def post(self, note_id):
        iden = int(note_id)
        note = db.get(db.Key.from_path('Notes', iden))
        note.author = self.request.get('author')
        note.text = self.request.get('text')
        note.priority = self.request.get('priority')
        note.status = self.request.get('status')
        note.date = datetime.now()
        note.put()
        return webapp2.redirect('/')

    def get(self, note_id):
      iden = int(note_id)
      note = db.get(db.Key.from_path('Notes', iden))
      user = users.get_current_user()
      self.render_template('edit.html', {'note': note, 'users': users})


class DeleteNote(BaseHandler):

    def get(self, note_id):
        iden = int(note_id)
        note = db.get(db.Key.from_path('Notes', iden))
        db.delete(note)
        return webapp2.redirect('/')


app = webapp2.WSGIApplication(
    [
     ('/', MainHandler),
     ('/create', CreateNote),
     ('/edit/([\d]+)', EditNote),
     ('/delete/([\d]+)', DeleteNote),
     (decorator.callback_path, decorator.callback_handler()),
    ],
    debug=True)
