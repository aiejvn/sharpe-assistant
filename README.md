# sharpe-assistant
An earpiece voice assistant. A voice-operated asynchronous agent network meant to make work light by leveraging agents for working on multiple things at once.

## TODO:

Sharpe Earpiece:
- [_] Convert all current LLM API calls to websocket calls
    - Cohere for internal reasoning
    - Perplexity for research/googling 
- [_] Track status of all async requests at a given moment
- [_] Implement parse tree for simple voice commands
    - Calendar Tool
    - Sending Messages Tool
- [_] Implement integration with google calendar, gmail, Discord
- [_] Implement sending responses/citations/search results to the user's email/phone 
- [_] Let the user interrupt the agent
- [_] Add OpenManus integration into back-end
    - Requires turning it into a package    

OpenManus Functionality:
- [X] Get OpenManus working 
- [X] Add generic output write of internal knowledge so far direct to markdown on failure to write before last step 
    - This was built in to OpenManus 

Due to current limitations in LLMs, commands should be effectively O(1) (i.e. instantly have a task, goal, context, and tool in mind) to keep speed managable

```"Many hands make light work." - John Heywood```