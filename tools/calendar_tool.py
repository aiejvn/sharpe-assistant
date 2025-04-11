import datetime
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

    
    def add_event(self, start_date:datetime.datetime, end_date:datetime.datetime, name="Upcoming Event"):
        pass

    def remove_event(self, date:datetime.datetime, end_date:datetime.datetime, name="Upcoming Event"):
        pass
    
    def read_events(self,
        start_date:datetime.datetime=datetime.datetime.now(),
        end_date:datetime.datetime=None,
        num_events=None
    )->list | None:
        if not num_events:
            num_events = 10
        
        try:
            # Debug:
            # end_date = start_date + datetime.timedelta(hours=8)
            
            # Call the Calendar API
            start_date = start_date.astimezone(datetime.timezone.utc).isoformat()
            
            # Replace "+00:00" with "Z" to make format Google-Parsable            
            start_date = start_date[:-6] + "Z"
            
            if end_date: 
                end_date = end_date.astimezone(datetime.timezone.utc).isoformat()
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
    print(cal.read_events())