from google.appengine.ext import db
from google.appengine.ext import blobstore

from datetime import datetime
from pytz.gae import pytz
from pytz import timezone

class Booking(db.Model):
  booking_ref = db.StringProperty(required=True)
  company = db.StringProperty(required=True)
  course = db.StringProperty(required=True)
  fare = db.FloatProperty(indexed=False)
  paid_by = db.DateProperty(default=None)
  state = db.CategoryProperty(default="UNPAID", choices=["UNPAID", "PAID", "CREDIT", "CANCELLED"])
  amount_in_credit = db.FloatProperty(default=None)
  credit_expiry = db.DateProperty(default=None)
  last_date = db.DateProperty(default=datetime.now(timezone('Australia/Sydney')).date())

  def __str__(self):
    return "{'booking_ref':"+str(self.booking_ref)+ \
            ",'company':"+str(self.company)+ \
            ",'course':"+str(self.course)+ \
            ",'fare':"+str(self.fare)+ \
            ",'paid_by':"+str(self.paid_by)+ \
            ",'state':"+str(self.state)+ \
            ",'amount_in_credit':"+str(self.amount_in_credit)+ \
            ",'credit_expiry':"+str(self.credit_expiry)+ \
            ",'last_date':"+str(self.last_date)+ \
            "}"

  def to_dict(self):
    return {
           'id': self.key().id(),
           'booking_ref': self.booking_ref,
           'company': self.company,
           'course': self.course,
           'fare': self.fare,
           'paid_by': self.paid_by,
           'state': self.state,
           'amount_in_credit': self.amount_in_credit,
           'credit_expiry': self.credit_expiry,
           }

class Passenger(db.Model):
  service_no = db.StringProperty(default=None)
  last_name = db.StringProperty(required=True)
  init = db.StringProperty(required=True)

  def __str__(self):
    return "{'service_no':"+str(self.service_no)+ \
            ",'last_name':"+str(self.last_name)+ \
            ",'init':"+str(self.init)+ \
            "}"

  def to_dict(self):
    return {
           'service_no': self.service_no,
           'last_name': self.last_name,
           'init': self.init,
           }

class Sector(db.Model):
  date = db.DateProperty(required=True)
  from_loc = db.StringProperty(required=True)
  to_loc = db.StringProperty(required=True)
  service = db.StringProperty(required=True)
  booking = db.ReferenceProperty(Booking, required=True, collection_name='sectors')

  def __str__(self):
    return "{'date':"+str(self.date)+ \
            ",'from_loc':"+str(self.from_loc)+ \
            ",'to_loc':"+str(self.to_loc)+ \
            ",'service':"+str(self.service)+ \
            ",'booking':"+str(self.booking)+ \
            "}"

  def to_dict(self):
    return {
           'id': self.key().id(),
           'date': self.date,
           'from_loc': self.from_loc,
           'to_loc': self.to_loc,
           'service': self.service,
           }

class Document(db.Model):
  date = db.DateProperty(required=True)
  blob_key = blobstore.BlobReferenceProperty(required=True)
  booking = db.ReferenceProperty(Booking, required=True, collection_name='documents')
  desc = db.TextProperty()

  def __str__(self):
    return "{'date':"+str(self.date)+ \
            ",'blob_key':"+str(self.blob_key)+ \
            ",'booking':"+str(self.booking)+ \
            ",'desc':"+str(self.desc)+ \
            "}"

  def to_dict(self):
    return {
           'id': self.key().id(),
           'date': self.date,
           'blob_key': self.blob_key,
           'desc': self.desc,
           }

class PassengerSectorBooking(db.Model):
  passenger = db.ReferenceProperty(Passenger, required=True, collection_name='bookings_rel')
  sector = db.ReferenceProperty(Sector, required=True, collection_name='passengers_rel')

  # Derived
  booking = db.ReferenceProperty(Booking, required=True, collection_name='passengers_rel')
  fare_type = db.TextProperty()

class LastUse(db.Model):
  obj = db.ReferenceProperty(db.Model, required=True, collection_name='last_use')
  last_use = db.DateProperty(default=datetime.now(timezone('Australia/Sydney')).date())

class Company(db.Model):
  name = db.StringProperty(required=True)

## TODO
def delete_stale_records():
  stale = LastUse.all()
  for s in stale:
    db.delete(s.obj)
  db.delete(stale.filter('last_use < ', _current_date() - _expiry_period))
