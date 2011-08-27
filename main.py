#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os
import sys

###os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

###from google.appengine.dist import use_library
###use_library('django', '1.2')

sys.path.insert(0, 'simplejson.zip')

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util

###from pytz.gae import pytz
###from pytz import timezone
from datetime import datetime

from views import views
from views import jsonfmt as fmt
import simplejson as json
import dateutil.parser

class JsonHandler(webapp.RequestHandler):
  def get(self, obj_type, arg=''):
    arg = arg.strip()
    if len(arg) > 0 and arg[-1] == '/':
      arg = arg[:-1]
    args = arg.strip().split('/')
    res = None

    if obj_type == 'booking':
      if len(args) > 1:
        if args[0] == 'id':
          res = views.get_booking_by_id(int(args[1]))
        elif args[0] == 'ref':
          ref = args[1]
          company = None
          if len(args) > 3 and args[2] == 'company':
            company = args[3]

          get_all = self.request.get('all', default_value='no').strip()
          active_only = (get_all != '')

          res = views.get_bookings_by_booking_ref(ref, company, active_only)
        elif args[0] == 'pax':
          sn = args[1]
          course = None
          if len(args) > 3 and args[2] == 'course':
            course = args[3]

          get_all = self.request.get('all', default_value='no').strip()
          active_only = (get_all != '')

          res = views.get_bookings_by_passenger_sn(sn, course, active_only)
      else:
        get_all = self.request.get('all', default_value='no').strip()
        active_only = (get_all != '')
        res = views.get_bookings(active_only)
    elif obj_type == 'sector':
      if args[0] == 'id':
        res = views.get_sector_by_id(int(args[1]))
      elif args[0] == 'pax':
        res = views.get_sectors_by_passenger_sn(args[1])
      elif args[0] == 'booking':
        res = views.get_sectors_by_booking_id(int(args[1]))
    elif obj_type == 'pax':
      if args[0] == 'id':
        res = views.get_passenger_by_sn(args[1])
      elif args[0] == 'name':
        init = None
        if len(args) > 3 and args[2] == 'init':
          init = args[3]
        res = views.get_passengers_by_name(args[1], init)
      elif args[0] == 'sector':
        res = views.get_passenger_fares_by_sector_id(int(args[1]))
    elif obj_type == 'doc':
      if args[0] == 'id':
        res = views.get_document_by_id(int(args[1]))
      elif args[0] == 'booking':
        res = views.get_document_by_booking_id(int(args[1]))
    elif obj_type == 'course':
      res = views.get_current_courses()

    self.response.out.write(json.dumps(res, default=fmt.json_handler))

class MainHandler(webapp.RequestHandler):
  def get(self, obj_type, arg=''):
    pass
  def put(self, obj_type, arg=''):
    pass
  def post(self, obj_type, arg=''):
    arg = arg.strip()
    if len(arg) > 0 and arg[-1] == '/':
      arg = arg[:-1]
    args = arg.strip().split('/')
    res = None

    if obj_type == 'booking':
      company = self.request.get('company', default_value=None)
      booking_ref = self.request.get('booking_ref', default_value=None)
      course = self.request.get('course', default_value=None)
      fare = self.request.get('fare', default_value=None)
      paid_by = self.request.get('paid_by', default_value=None)
      state = self.request.get('status', default_value=None)
      amount_in_credit = self.request.get('credit', default_value=None)
      credit_expiry = self.request.get('credit_expiry', default_value=None)

      kwds = {}
      if fare and len(fare.strip()) > 0:
        kwds['fare'] = float(fare)
      if paid_by and len(paid_by.strip()) > 0:
        kwds['paid_by'] = dateutil.parser.parse(paid_by).date()
      if state and len(state.strip()) > 0:
        kwds['state'] = state
      if amount_in_credit and len(amount_in_credit.strip()) > 0:
        kwds['amount_in_credit'] = float(amount_in_credit)
      if credit_expiry and len(credit_expiry.strip()) > 0:
        kwds['credit_expiry'] = dateutil.parser.parse(credit_expiry).date()

      if company and booking_ref and course:
        res = views.add_booking(company, booking_ref, course, **kwds)

    elif obj_type == 'sector':
      views.delete_sector_by_id(int(args[0]))
    elif obj_type == 'pax':
      if args[1] == 'sector':
        views.remove_pax_from_sector(int(args[2]), args[0])
      elif args[1] == 'booking':
        views.remove_pax_from_booking(int(args[2], args[0]))
    elif obj_type == 'doc':
      views.delete_document_by_id(int(args[0]))
    
    self.response.out.write(json.dumps(res, default=fmt.json_handler))

  def delete(self, obj_type, arg=''):
    arg = arg.strip()
    if len(arg) > 0 and arg[-1] == '/':
      arg = arg[:-1]
    args = arg.strip().split('/')
    res = None

    if obj_type == 'booking':
      views.delete_booking_by_id(int(args[0]))
    elif obj_type == 'sector':
      views.delete_sector_by_id(int(args[0]))
    elif obj_type == 'pax':
      if args[1] == 'sector':
        views.remove_pax_from_sector(int(args[2]), args[0])
      elif args[1] == 'booking':
        views.remove_pax_from_booking(int(args[2], args[0]))
    elif obj_type == 'doc':
      views.delete_document_by_id(int(args[0]))

def main():
  application = webapp.WSGIApplication([
                                        (r'/json/(.*?)/(.*)', JsonHandler),
                                        (r'/json/(.*)', JsonHandler),
                                        (r'/(.*?)/(.*)', MainHandler),
                                        (r'/(.*)', MainHandler),
                                       ], debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()
