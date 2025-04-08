# sharpe-assistant
An earpiece voice assistant. A voice-operated asynchronous agent network meant to make work light by leveraging agents for working on multiple things at once.

## TODO:
- [X] Get OpenManus working 
- [_] Convert all current API calls to websocket calls
- [_] Implement parse tree for simple voice commands using MCP architecture
    - Reasoning tool, Agentic tool, email tool, calendar tool, etc.
    - Parse tree should handle voice input, other stuff should go to tools folder
- [_] Implement integration with google calendar
- [_] Implement sending responses/citations/search results to the user's email/phone 
- [_] Implement (SAFELY) reading from a user's local storage in certain prompt cases
- [_] Convert requests to asynchronous network
- [_] Track status of all async requests at a given moment
- [_] Let the user interrupt the agent


```"Many hands make light work." - John Heywood```