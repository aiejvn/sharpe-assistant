import datetime as dt
from datetime import datetime, timedelta
from dateutil import parser, relativedelta
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError



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


    def string_to_datetime(self, time:str)->datetime:
        """
            Given a string like "Monday", find the date of the soonest Monday and return it as a String.
            Given a string like "April 18th", find the date of the soonest April 18th and return it as a String.
        """
        reference_date = datetime.now()
        
        try:
            # Try to parse absolute date first (i.e. "April 19th")
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

    
    def add_event(self, start_date:str, end_date:str, name="Upcoming Event", location=""):
        """
            Adds an event to the Google Calendar.
            Requires string_to_datetime to be able to parse times in dates.
        """
        # Subtract 3 hours from start dates and end dates 
        start_date = self.string_to_datetime(start_date) - timedelta(hours=3)        
        start_date = start_date.astimezone(dt.timezone.utc).isoformat()
            
        end_date = self.string_to_datetime(start_date) - timedelta(hours=3)
        end_date = end_date - timedelta(hours=3)
        end_date = end_date.astimezone(dt.timezone.utc).isoformat()
        
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
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 10},
                ],
            },
        }

        event = cal.service.events().insert(calendarId='primary', body=event).execute()
        print('Event created: %s' % (event.get('htmlLink')))


    def remove_event(self, start_date:str, end_date:str, name="Upcoming Event"):
        pass

    
    def read_events(self,
        start_date:str,
        end_date:str=None,
        num_events=None
    )->list | None:
        if not num_events:
            num_events = 10
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
            
            events_result = (
                self.service.events()
                .list(
                    calendarId="primary",
                    timeMin=start_date,
                    timeMax=end_date,
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
                print(start, event["summary"])
                
            return [event['summary'] for event in events]

        except HttpError as error:
            print(f"An error occurred: {error}")
    
    
if __name__ == '__main__':
    cal = CalendarTool()
    
    # Parse test cases
    print(cal.string_to_datetime("Monday 11 o'clock"))
        # Doesn't work (at least not yet)
        
    # Below works
    # print(cal.string_to_datetime("Monday"))
    # print(cal.string_to_datetime("April 19th"))
    # print(cal.string_to_datetime("March 10th"))
    
    # Test reading events - works
    print(cal.read_events(start_date="April 11th"))
    
    # Debugging calendar adding an event
    event = {
        'summary': 'Google I/O 2015',
        'location': '',
        'description': 'A chance to hear more about Google\'s developer products.',
        'start': {
            # 'dateTime': '2025-04-11T09:00:00-07:00',
            'dateTime': '2025-04-11T01:00:00.460840',
            'timeZone': 'America/Los_Angeles',
        },
        'end': {
            # 'dateTime': '2025-04-11T17:00:00-07:00',
            'dateTime': '2025-04-11T09:00:00.460840',
            'timeZone': 'America/Los_Angeles',
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
            {'method': 'email', 'minutes': 24 * 60},
            {'method': 'popup', 'minutes': 10},
            ],
        },
    }

    event = cal.service.events().insert(calendarId='primary', body=event).execute()
    print('Event created: %s' % (event.get('htmlLink')))