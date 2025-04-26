import datetime as dt
from datetime import datetime, timedelta
from dateutil import parser, relativedelta
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import re

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

class CalendarTool:
    def __init__(self):
        creds = None
  
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
                creds = flow.run_local_server(port=0)
                
            # Save the credentials for the next run
            with open("token.json", "w") as token:
                token.write(creds.to_json())

        # Calendar Object  
        self.service = build("calendar", "v3", credentials=creds)
        if not self.service:
            AssertionError("Could not initialize calendar.")
            
        try:
            calendar_list = self.service.calendarList().list().execute()
            # for calendar in calendar_list['items']:
            #     print(f"Calendar Name: {calendar['summary']}, Calendar ID: {calendar['id']}")
            self.calendarType = next(
                (calendar['id'] for calendar in calendar_list['items'] if calendar['summary'] == "Test Calendar"),
                None
            )
            # print(self.calendarType)
            if not self.calendarType:
                raise ValueError("Test Calendar not found.")
        except Exception as e:
            print(f"An error occurred while fetching calendar IDs: {e}")
            raise
            

    def make_string_parsible(self, timestr:str)->str:
        """
            Make a string parsable for string_to_datetime.
            E.g. all below dates should translate to upcoming Monday, 11AM.
            
            "Monday 11 o'clock" [Doesn't work]
            "Monday 11 AM" [Doesn't work]
            "Monday 11:00" [Works]
            "Monday 11" [Doesn't work]
        """
        timestr = re.sub(r"(\d+)\s*o'clock", r"\1:00", timestr, flags=re.IGNORECASE)  # Convert "o'clock" to ":00"
        timestr = re.sub(r"(\d+)\s*(AM|PM)", r"\1:00", timestr, flags=re.IGNORECASE)  # Convert "AM/PM" to ":00"
        timestr = re.sub(r"(\d+)\s+(\d{2})", r"\1:\2", timestr) # Convert "{Hour} {Minute}" to "{Hour}:{Minute}""
        timestr = re.sub(r"(\d+)\s*$", r"\1:00", timestr)  # Add ":00" if only the hour is provided (and if our time doesn't match to above case)

        return timestr
        


    def string_to_datetime(self, time:str)->datetime:
        """
            Given a string like "Monday", find the date of the soonest Monday and return it as a String.
            Given a string like "April 18th", find the date of the soonest April 18th and return it as a String.
        """
        reference_date = datetime.now()
        
        try:
            # Try to parse absolute date first (i.e. "April 19th")
            time = self.make_string_parsible(time)
            parsed_date = parser.parse(time, default=reference_date)
            
            # If parsed date is in the past, move to the next year (for annual dates like "April 19th")
                # fuzzy = true removes noise from the string
                # fuzzy_with_true allows parsing of spoken times
            if parsed_date < reference_date:
                if parser.parse(time, fuzzy=True).year == parsed_date.year:
                    parsed_date = parsed_date.replace(year=parsed_date.year + 1)
            
            return parsed_date
        except Exception as e:
            print("Could not parse date:", e)

    
    def add_event(self, start_date:str, end_date:str, name="Upcoming Event", location="")->str:
        """
            Adds an event to the Google Calendar.
            Requires string_to_datetime to be able to parse times in dates.
        """
        try:
            # Subtract 3 hours from start dates and end dates 
            start_date = self.string_to_datetime(start_date)     
            start_date = start_date.astimezone(dt.timezone.utc).isoformat()
                
            end_date = self.string_to_datetime(end_date)
            end_date = end_date.astimezone(dt.timezone.utc).isoformat()
            
            # print(start_date, "\n", end_date)
            
            event = {
                'summary': name,
                'location': location,
                'description': 'Event created by Sharpe.',
                'start': {
                    'dateTime': start_date, 
                    'timeZone': "Canada/Eastern", # Random +3 hours???
                },
                'end': {
                    'dateTime': end_date,
                    'timeZone': "Canada/Eastern",
                },
                'recurrence': [
                    # 'RRULE:FREQ=DAILY;COUNT=1'
                ],
                'attendees': [
                    # {'email': 'lpage@example.com'},
                    # {'email': 'sbrin@example.com'},
                ],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                    # {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 30},
                    ],
                },
                'colorId': 3
            }

            event = self.service.events().insert(calendarId=self.calendarType, body=event).execute()
            success_str = 'Event created: %s' % (event.get('htmlLink'))
            print(success_str)
            return success_str
        
        except Exception as e:
            fail_str = f"An exception occurred: {e}"
            print(fail_str)
            return fail_str
        

    def remove_event(self, event_index:int, event_list:list)->str:
        """
            Remove an event from a user's calendar.
            Users should do so using the event list ID, like navigating a phone menu.
        """
        try:
            event_id = event_list[event_index][1]
            self.service.events().delete(calendarId=self.calendarType, eventId=event_id).execute()
            
            success_str = 'Event deleted: %s' % (event_list[event_index][0] + " : " + event_list[event_index][1])
            event_list.pop(event_index) # Remove the event from the local list of events, in-place.
            
            print(success_str)
            return success_str
        
        except Exception as e:
            fail_str = f"An exception occurred: {e}"
            print(fail_str)
            
            return fail_str
        
    def update_event(self, event_index:int, feature:str, new_value:str, event_list:list)->str:
        """
            Edit an event in the user's calendar. 
            Users should do so using the event list ID, like navigating a phone menu.
        """
        try:
            event_id = event_list[event_index][1]
            
            # Retrieve the event from the API.
            event = self.service.events().get(calendarId=self.calendarType, eventId=event_id).execute()

            match feature.lower():
                case "start time":
                    start_date = self.string_to_datetime(new_value)     
                    start_date = start_date.astimezone(dt.timezone.utc).isoformat()
                    # print(start_date)
                    event['start']['datetime'] = start_date 
                
                case "end time":
                    end_date = self.string_to_datetime(new_value)     
                    end_date = end_date.astimezone(dt.timezone.utc).isoformat()
                    # print(end_date)
                    event['end']['datetime'] = end_date 
                
                case "location":
                    event['location'] = new_value

                case "summary":
                    event['summary'] = new_value
                
                case _:
                    ValueError("Could not match input feature to any implemented feature.")
            # event[feature] = new_value

            updated_event = self.service.events().update(calendarId=self.calendarType, eventId=event['id'], body=event).execute()
            
            success_str = 'Event updated: %s' % (event_list[event_index][0] + " : " + event_list[event_index][1])
            
            print(success_str)
            return success_str
        
        except Exception as e:
            fail_str = f"An exception occurred: {e}"
            print(fail_str)
            
            return fail_str
    
    def read_events(self,
        start_date:str,
        end_date:str=None,
        num_events:int=10
    )->list | None:
        start_date = self.string_to_datetime(start_date)
        if end_date: end_date = self.string_to_datetime(end_date)
        
        
        # Convert start dates from String Input to Datetime objects
        
        try:
            # Debug:
            # end_date = start_date + datetime.timedelta(hours=8)
            
            # Call the Calendar API
            start_date = start_date.astimezone(dt.timezone.utc).isoformat()
            
            # Replace "+00:00" with "Z" to make format Google-Parsable            
            start_date = start_date[:-6] + "Z"
            
            if end_date: 
                end_date = end_date.astimezone(dt.timezone.utc).isoformat()
                end_date = end_date[:-6] + "Z"
            
            if end_date:
                events_result = (
                    self.service.events()
                    .list(
                        calendarId=self.calendarType,
                        timeMin=start_date,
                        timeMax=end_date,
                        maxResults=num_events,
                        singleEvents=True,
                        orderBy="startTime",
                    )
                    .execute()
                )
            else:
                events_result = (
                    self.service.events()
                    .list(
                        calendarId=self.calendarType,
                        timeMin=start_date,
                        maxResults=num_events,
                        singleEvents=True,
                        orderBy="startTime",
                    )
                    .execute()
                )
                
            events = events_result.get("items", [])

            if not events:
                print("No upcoming events found.")
                return

            # Prints the start and name of the next 10 events
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                print(start, event["summary"], f"id:{event['id']}")
                
            return [(event['summary'], event['id']) for index, event in enumerate(events)]

        except HttpError as error:
            print(f"An error occurred: {error}")
    
    
# Note: We may need to refresh the token every now and then by deleting token.json. 
if __name__ == '__main__':
    cal = CalendarTool()
    
    # Parse test cases
    # print("Monday 11 o'clock,", cal.string_to_datetime("Monday 11 o'clock"))
    # print("Monday 11 AM,", cal.string_to_datetime("Monday 11 AM"))
    # print("Monday 11:00,", cal.string_to_datetime("Monday 11:00"))
    # print("Monday 11,", cal.string_to_datetime("Monday 11"))    
    # print("Monday 11 29,", cal.string_to_datetime("Monday 11 29")) # Should give 11:25. Actually gives 11-25 (November 25)    
    # print(cal.string_to_datetime("Monday"))
    # print(cal.string_to_datetime("April 19th"))
    # print(cal.string_to_datetime("March 10th"))
    
    
    # Test adding events - works so far
    cal.add_event(start_date="Monday 10 30", end_date="Monday 12", name="Sharpe Test Event", location="Super Secret Warehouse")
    cal.add_event(start_date="Monday 10 30", end_date="Monday 15", name="Sharpe Test Event", location="Office 42")
    
    # Test reading events - works, but not if start date is in the past?
    events = cal.read_events(start_date="April 25th")
    for i in range(len(events)):
        print(i, ":", events[i])
    
    # Test updating events
        # BUG: CANNOT UPDATE FOR DATES BEYOND CURRENT DATE 
    index = next((i for i, event in enumerate(events) if event[0] == "Sharpe Test Event"), None)
    cal.update_event(index, feature="end time", new_value="Tuesday 15", event_list=events)
    cal.update_event(index, feature="summary", new_value="Testing editing Sharpe", event_list=events)
    cal.update_event(index, feature="location", new_value="Sharpeland", event_list=events)
        
    # Test removing events 
    for i in range(3): # 1-2 should succeed, 3rd iteration should fail
        index = next((i for i, event in enumerate(events) if event[0] == "Sharpe Test Event"), None)
        cal.remove_event(index, events)