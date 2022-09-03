class EventAttendee(models.Model):
    '''Created when form filled out at event registration page'''
    email = models.EmailField('Email Address')
    first_name = models.CharField('First Name', max_length=50)
    last_name = models.CharField('Last Name', max_length=50)
    # Other personal fields

    @property
    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'

    def __str__(self):
        return self.get_full_name
    
    @property
    def get_upcoming_bookings(self):
        return EventBooking.objects.filter(attendee=self, 
            event__event_date__gte=timezone.now()).order_by('event__event_date')


class Event(models.Model):
    '''Gets created when Event Page gets published on site'''
    event_page = models.ForeignKey('website.EventPage', on_delete=models.SET_NULL, null=True)
    event_name = models.CharField(max_length=300)
    event_date = models.DateTimeField()
    is_live_event = models.BooleanField(default=False) # Meaning not a virtual event
    can_register = models.BooleanField(default=True)
    attendees = models.ManyToManyField(
        EventAttendee, 
        through='EventBooking',
        through_fields=('event', 'attendee'),
    )

    @staticmethod
    def make_or_update(event_page): 
        if not event_page.can_register:
            return
        e_name = event_page.title
        # Grabs next future event date or returns nothing
        try:
            e_date = event_page.most_recent_occurrence[0]
        except TypeError:
            return
        # Check if already exists & update if changes
        try:
            obj = Event.objects.get(event_page=event_page)
            updated_fields = []
            if e_name != obj.event_name:
                obj.event_name = e_name
                updated_fields.append('event_name')
            if e_date != obj.event_date:
                obj.event_date = e_date
                updated_fields.append('event_date')
            if event_page.is_live_event != obj.is_live_event:
                obj.is_live_event = event_page.is_live_event
                updated_fields.append('is_live_event')
            if event_page.can_register != obj.can_register:
                obj.can_register = event_page.can_register
                updated_fields.append('can_register')
            if updated_fields:
                obj.save(update_fields=updated_fields)
        # Make new Event if not exist
        except Event.DoesNotExist:
            obj = Event(event_page=event_page,
                event_name=e_name,
                event_date=e_date,
                is_live_event=event_page.is_live_event
            )
            obj.save()
        return

    #Removes event from event reg form
    @staticmethod
    def remove_registration(event_page):
        event = Event.objects.get(event_page=event_page)
        event.can_register = False
        event.save()
        return
            

    @property
    def get_date(self):
        return self.event_date.strftime('%a, %B %d, %Y')

    def __str__(self):
        return f'{self.event_name} - {self.get_date}'


class EventBooking(models.Model):
    '''Records events for EventAttendee based on events checked on event-registration form'''
    event = models.ForeignKey(Event, null=True, on_delete=models.SET_NULL)
    attendee = models.ForeignKey(EventAttendee, on_delete=models.CASCADE)
    time_registered = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f'{self.event.event_name}: {self.attendee}'

    @staticmethod
    def add_bookings(attendee, checked_events):
        # Ensures no duplicate attendee-eventbookings
        prev_bookings = [e.id for e in attendee.event_set.all()]
        new_bookings = [EventBooking(event=e, 
                        attendee=attendee) for e in checked_events.exclude(id__in=prev_bookings)]
        Event.attendees.through.objects.bulk_create(new_bookings)
        return
