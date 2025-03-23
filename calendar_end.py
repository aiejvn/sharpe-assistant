import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import re

"""
    TODO: Implement a class whose functions interact with Google calendar.
    We will call the following functions based if the user has 'Add Event', 'Read Event', or 'Delete Event' in transcription 
                                            
"""

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

class CalendarManager:
    def __init___(self):
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

        # ------- CALENDAR ------- 
        self.service = build("calendar", "v3", credentials=creds)
        if not self.service:
            AssertionError("Could not initialize calendar.")

    
    def add_event(self, start_date:datetime.datetime, end_date:datetime.datetime, name="Upcoming Event"):
        pass

    def remove_event(self, date:datetime.datetime, end_date:datetime.datetime, name="Upcoming Event"):
        pass
    
    def read_events(self, 
                    start_date:datetime.datetime, 
                    end_date:datetime.datetime=datetime.datetime.now(), 
                    name="Upcoming Event"):
        try:
            # Call the Calendar API
            events_result = (
                self.service.events()
                .list(
                    calendarId="primary",
                    timeMin=start_date,
                    timeMax=end_date,
                    maxResults=10,
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
    cal = CalendarManager()