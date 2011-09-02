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

def parse_date(s):
  return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.Z")

class MainHandler(webapp.RequestHandler):
  def get(self, obj_type, arg=''):
    arg = arg.strip()
    if len(arg) > 0 and arg[-1] == '/':
      arg = arg[:-1]
    args = arg.strip().split('/')
    res = None

    if obj_type == 'booking':
      # /booking
      if len(args) == 1 and len(args[0].strip()) > 0:
        get_all = self.request.get('all', default_value='no').strip()
        active_only = (get_all != 'no')

        if args[0] == 'search':
          # /booking/search?
          search_by = self.request.get('search_by', default_value='ref')

          if search_by == 'ref':
            # /booking/search?search_by=ref&ref=<ref>[&company=<company>]
            ref = self.request.get('ref', default_value=None)
            company = self.request.get('company', default_value=None)

            res = views.get_bookings_by_booking_ref(ref, company, active_only)
          elif search_by == 'pax':
            # /booking/search?search_by=pax&service_no=<service_no>[&course=<course>]
            sn = self.request.get('service_no', default_value=None)
            course = self.request.get('course', default_value=None)

            res = views.get_bookings_by_passenger_sn(sn, course, active_only)
        elif args[0] == 'unpaid':
          res = views.get_bookings(active_only, 'UNPAID')['UNPAID']
        elif args[0] == 'paid':
          res = views.get_bookings(active_only, 'PAID')['PAID']
        elif args[0] == 'credit':
          res = views.get_bookings(active_only, 'CREDIT')['CREDIT']
        elif args[0] == 'cancelled':
          res = views.get_bookings(active_only, 'CANCELLED')['CANCELLED']
        else:
          # /booking/<id>
          res = views.get_booking_by_id(int(args[0]))
      elif len(args) > 1:
        if args[1] == 'sector':
          # /booking/<id>/sector
          res = views.get_sector_by_booking_id(int(args[0]))
        elif args[1] == 'pax':
          # /booking/<id>/pax
          res = views.get_passenger_by_booking_id(int(args[0]))
        elif args[1] == 'doc':
          # /booking/<id>/doc
          res = views.get_document_by_booking_id(int(args[0]))
      else:
        # /booking
        get_all = self.request.get('all', default_value='no').strip()
        active_only = (get_all != 'no')
        res = views.get_bookings(active_only)
    elif obj_type == 'sector':
      # /sector
      if len(args) == 1 and len(args[0].strip()) > 0:
        # /sector/<id>
        res = views.get_sector_by_id(int(args[0]))
      elif len(args) == 2:
        # /sector/<id>/pax
        res = view.get_passenger_fares_by_sector_id(int(args[0]))
    elif obj_type == 'pax':
      # /pax
      if len(args) == 1 and args[0] == 'search':
        # /pax/search?last_name=<last_name>[&init=<init>]
        last_name = self.request.get('last_name', default_value=None)
        init = self.request.get('init', default_value=None)

        res = views.get_passengers_by_name(last_name, init)
      elif len(args) == 1 and len(args[0].strip()) > 0:
        # /pax/<service_no>
        res = view.get_passenger_by_sn(args[0])
      elif len(args) > 1:
        sn = args[0].strip()

        if args[1] == 'sector':
          # /pax/<service_no>/sector
          res = get_sectors_by_passenger_sn(sn)
        elif args[1] == 'booking':
          # /pax/<service_no>/booking
          res = get_bookings_by_passenger_sn(sn)
    elif obj_type == 'doc':
      # /doc/<id>
      assert (len(args) == 1 and len(args[0].strip() > 0))
      res = views.get_document_by_id(int(args[0]))
    elif obj_type == 'course':
      # /course
      res = views.get_current_courses()
    elif obj_type == 'company':
      # /company
      res = views.get_companies()

    self.response.out.write(json.dumps(res, default=fmt.json_handler))

  def put(self, obj_type, arg=''):
    arg = arg.strip()
    if len(arg) > 0 and arg[-1] == '/':
      arg = arg[:-1]
    args = arg.strip().split('/')
    obj_id = args[0]
    res = None

    if obj_type == 'booking':
      if len(args) == 0:
        # /booking/<id>
        # Create new booking
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
          kwds['paid_by'] = parse_date(paid_by).date()
        if state and len(state.strip()) > 0:
          kwds['state'] = state
        if amount_in_credit and len(amount_in_credit.strip()) > 0:
          kwds['amount_in_credit'] = float(amount_in_credit)
        if credit_expiry and len(credit_expiry.strip()) > 0:
          kwds['credit_expiry'] = parse_date(credit_expiry).date()

        if company and booking_ref and course:
          res = views.update_booking(int(obj_id), **kwds)

    elif obj_type == 'sector':
      if len(args) == 1:
        # /sector/<id>
        # Update sector
        date = self.request.get('date', default_value=None)
        from_loc = self.request.get('from', default_value=None)
        to_loc = self.request.get('to', default_value=None)
        service = self.request.get('service', default_value=None)

        kwds = {}
        if date:
          kwds['date'] = parse_date(date.strip())
        if from_loc:
          kwds['from_loc'] = from_loc.strip()
        if to_loc:
          kwds['to_loc'] = to_loc.strip()
        if service:
          lwds['service'] = service.strip()

        if date and from_loc and to_loc and service:
          res = views.update_sector(int(obj_id), **kwds)
      elif len(args) == 3 and args[1] == 'pax':
        # /sector/<id>/pax/<service_no>
        # Update fare
        sn = args[2]
        fare = self.request.get('fare', default_value=None)
        res = update_passenger_fare(sn, int(obj_id), fare)

    elif obj_type == 'pax':
      # /pax/<service_no>
      # Update passenger
      kwds = {}
      kwds['last_name'] = self.request.get('last_name', default_value=None)
      kwds['init'] = self.request.get('init', default_value=None)

      res = update_passenger(obj_id, **kwds)
    
    self.response.out.write(json.dumps(res, default=fmt.json_handler))

  def post(self, obj_type, arg=''):
    arg = arg.strip()
    if len(arg) > 0 and arg[-1] == '/':
      arg = arg[:-1]
    args = arg.strip().split('/')
    res = None

    if obj_type == 'booking':
      if len(args) == 0:
        # /booking
        # Create new booking
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
          kwds['paid_by'] = parse_date(paid_by).date()
        if state and len(state.strip()) > 0:
          kwds['state'] = state
        if amount_in_credit and len(amount_in_credit.strip()) > 0:
          kwds['amount_in_credit'] = float(amount_in_credit)
        if credit_expiry and len(credit_expiry.strip()) > 0:
          kwds['credit_expiry'] = parse_date(credit_expiry).date()

        if company and booking_ref and course:
          res = views.add_booking(company, booking_ref, course, **kwds)

      elif args[2] == 'sector':
        # /booking/<booking_id>/sector
        # Add sector to booking
        booking_id = int(args[0].strip())
        date = self.request.get('date', default_value=None)
        from_loc = self.request.get('from', default_value=None)
        to_loc = self.request.get('to', default_value=None)
        service = self.request.get('service', default_value=None)

        kwds = {}
        if date:
          kwds['date'] = parse_date(date.strip())
        if from_loc:
          kwds['from_loc'] = from_loc.strip()
        if to_loc:
          kwds['to_loc'] = to_loc.strip()
        if service:
          lwds['service'] = service.strip()

        if date and from_loc and to_loc and service:
          res = views.add_sector(booking_id, **kwds)

    elif obj_type == 'sector':
      if len(args) > 2 and args[1] == 'pax':
        sector_id = int(args[0].strip())
        sn = self.request.get('service_no', default_value=None)
        last_name = self.request.get('last_name', default_value=None)
        init = self.request.get('init', default_value=None)
        fare = self.request.get('fare', default_value=None)

        if last_name is None or len(last_name.strip()) == 0:
          res = add_passenger_to_sector(sector_id, sn)
        else:
          res = add_passenger_to_sector(sector_id, sn, last_name, init, fare)
    
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
                                        (r'/(.*?)/(.*)', MainHandler),
                                        (r'/(.*)', MainHandler),
                                       ], debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()
