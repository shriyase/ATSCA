# %% [markdown]
# Extracting User's Google Calendar

# %%
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import googleapiclient.discovery
import datetime
import streamlit as st

# %%
import methods  # file containing functions to interact with Google calendar like add event, create event, etc
import json
import re

st.title("Automated Task Scheduler and Calendar Assistant")
st.write(
    "Hey there! I'm your virtual assistant. I can help you manage your calendar and schedule tasks. How can I assist you today?"
)


google_calendar = (
    methods.get_google_calendar_service()
)  # get the google calendar service
tasks = methods.get_task_service()  # get the task service
tasks_list = methods.extractTasks(tasks)
calendar = methods.extractCalendar(
    google_calendar
)  # extract the calendar from the service
client = methods.set_up_ChatGPT(calendar, tasks_list)  # set up the ChatGPT model
now = methods.current_time()

# %% [markdown]
# Logging Previous Conversation


# %%
def log_activity(role, message):
    filename = f"activity_log.txt"
    with open(filename, "a") as file:
        timestamp = datetime.datetime.now().isoformat()
        file.write(f"{timestamp} | {role}: {message}\n")


# %%
def log_message(role, message):
    filename = f"conversation_log.txt"
    with open(filename, "a") as file:
        timestamp = datetime.datetime.now().isoformat()
        file.write(f"{timestamp} | {role}: {message}\n")


# %%
def get_past_conversation():
    filename = f"conversation_log.txt"
    try:
        with open(filename, "r") as file:
            return file.read()
    except FileNotFoundError:
        return ""


# %% [markdown]
# Get User's Query

# %%
past_conversation = get_past_conversation()
# schedule tasks or calendar events

context = f"Here's my calendar and To-Do list for the week, store it for your reference. Calendar: {calendar}\n To-Do Tasks: {tasks_list} Today's date and time is: {now}\n"
instruction = """\nAs my trusted virtual assistant, you are an expert in adeptly managing my calendar and assisting with scheduling tasks. Here is what I need from you:

1. **Calendar Management**:
 You have the capability to create, adjust, oversee, list, update, delete, and handle recurring events on my calendar as per my requests.
    - In situations where I don't provide enough information, you can ask for more details, upto 4 times, otherwise use your best judgement.
    - Should an event require scheduling or rescheduling and I haven't provided a specific time, consult my calendar and deduce a suitable time slot using your best judgement. Consider my usual habits, such as meal and sleep times, and assume a standard event duration of 1 hour unless your judgement suggests otherwise based on the nature of the event.
    - Before confirming any scheduling actions, scrutinize for any possible scheduling conflicts.
    - Always ask for confirmation before making any changes to the calendar. If I reject the suggested time, offer an alternative time slot.
    - Inform me when you have successfully completed your task and ensure there are no more pending queries from your end, otherwise always end with a question mark. 
   
2. **Task Scheduling**:
You have the capability to schedule tasks from my To-Do list into my calendar.
    - Utilize your best judgement to organize and propose times for scheduling tasks listed in my To-Do list. Prioritize tasks based on urgency and balance throughout the available slots in my schedule.
    - Verify the calendar to ensure a task isn't already scheduled before adding it.
    - Check for any conflicts that may arise due to overlapping tasks or events.
    - Present a thoughtful plan for the scheduled tasks. Use your best judgement to predict task durations based on the nature of each task.
    - Ask for my confirmation before finalizing the schedule. 
    - If I disagree with the proposed times, offer alternatives based on my feedback.
    - Always end your messages with a question mark to indicate that you are seeking a response from me, unless it's a confirmation of a task completion.

For example, if I request: 'Schedule a meeting with the design team on Wednesday,' your response might be: 'Based on your current calendar, Wednesday 10 AM is available and seems like a quiet time for you. Should I schedule the meeting for then?' 
Example request: 'schedule all my tasks'
Example response: 'Sure! Here's a proposed schedule for all your tasks. Is there anything you'd like to change?
- Task 1: Apr 2nd, 10:00 AM - 11:00 AM
- Task 2: Apr 2nd, 11:00 AM - 12:00 PM
- Task 3: Apr 2nd, 12:00 PM - 1:00 PM
Please perform the necessary actions using the Google Calendar API.\n
Here's the previous conversation with the user, read it and understand user preferences if any, use it to make your best judgement on scheduling.\n"""
# initial setup

initial_prompt = context + instruction + past_conversation

# %%
user_request = st.text_input("Enter your query here")
combined_prompt = initial_prompt + "\nUser request: " + user_request


# %%
def chat_gpt(client, messages):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo", messages=messages, max_tokens=500
    )
    return response.choices[0].message.content


messages = [
    {"role": "system", "content": initial_prompt},
    {"role": "user", "content": user_request},
]
log_activity("system", context + instruction)
log_activity("user", user_request)

log_message("user", user_request)

# %%
finalized_response = False

# establishing feedback loop to chat with user
while not finalized_response:
    response = chat_gpt(client, messages)
    log_activity("assistant", response)
    st.write(response)
    log_message("assistant", response)
    messages.append({"role": "assistant", "content": response})
    if re.compile(r"\?").search(response):
        finalized_response = False
        user_feedback = st.text_input("Feedback")
        messages.append({"role": "user", "content": user_feedback})
        log_message("user", user_feedback)
        log_activity("user", user_feedback)
    else:
        finalized_response = True


# %%
# get GPT to output the function calls I need to make to the calendar API
instruction2 = """\nBased on the user's request you've just processed, please output the appropriate function call(s) to interact with the Google Calendar API. Format your response as a single string containing one or more function calls separated by semicolons. Do not include explanations or additional text. If there is no action required then output an empty string.
All dates should be in 'YYYY-MM-DD' format, and times should be in 24-hour format 'HH:MM'. Additionally, assume default duration as 1 hour for any event. Use createEvent for scheduling tasks on the to-do list.
Available function templates to include in the response string:
- createEvent(description, date, time, duration)
- moveEvent(event_id, new_date, new_time)
- updateEvent(event_id, new_color, new_duration, new_location)
- deleteEvent(event_id)
- createRecurringEvent(description, start_date, time, duration, frequency, until_date). Frequency can have the value of DAILY, WEEKLY, MONTHLY, YEARLY.
- deleteRecurringEvent(recurring_event_id) 
- updateRecurringEvent(recurring_event_id, new_color, new_duration, new_location, new_frequency, new_until)
For all functions other than createEvent and createRecurringEvent, make sure to fill in the id of the event you are referring to from the calendar provided.
Make sure to fill in the required information, such as event names, dates, times, etc., based on the user's request context. Replace placeholders like 'today' or 'tomorrow' with specific dates in the format YYYY-MM-DD. If more details are needed from the user for a function call, use your best judgment to complete the function with the information available.
Example input1: Schedule a team meeting for Friday afternoon at 3pm
Example output1: createEvent("Team Meeting", "YYYY-MM-DD", "15:00", 1:00)
Example input2: Update my team meeting to be two hours
Example output2: updateEvent("event_id", '', 2:00, '')
Example input3: Create a recurring meeting every Wednesday at 2pm until the end of June
Example output3: createRecurringEvent("Meeting", "YYYY-MM-DD", "02:00", "1:00", "WEEKLY", "YYYY-MM-DD")
Example input4: Update my recurring meeting every Wednesday at 2pm to be every month until the end of August
Example output4: updateRecurringEvent("RecurringEventId", "", "02:00", "1:00", "", "MONTHLY", "YYYY-MM-DD")
Example input5: Move my team meeting to tomorrow at 12pm
Example output5: moveEvent("event_id", 'YYYY-MM-DD', '12:00')
Example input6: Clear my afternoon
Example output7: deleteEvent("event_id");deleteEvent("event_id")
Example input8: Schedule all my tasks
Example output8: createEvent("Task 1", "YYYY-MM-DD", "10:00", 1:00);createEvent("Task 2", "YYYY-MM-DD", "11:00", 1:00);createEvent("Task 3", "YYYY-MM-DD", "12:00", 1:00)\n

Now, please generate the necessary function call(s) based on the user's request."""

# %%
messages.append({"role": "system", "content": instruction2})
log_activity("system", instruction2)
function_call = chat_gpt(client, messages)
log_activity("assistant", function_call)
print(function_call)
# Example of function call: createEvent("Meeting with John", "2022-12-31", "10:00 AM", 2)

# %%
if "(" in function_call:
    function_calls = [line.strip() for line in function_call.split(";")]
    print(function_calls)

    # Define a dictionary mapping function names to their corresponding Python functions
    functions = {
        "createEvent": methods.createEvent,
        "moveEvent": methods.moveEvent,
        "updateEvent": methods.updateEvent,
        "deleteEvent": methods.deleteEvent,
        "createRecurringEvent": methods.createRecurringEvent,
        "updateRecurringEvent": methods.updateRecurringEvent,
        "deleteRecurringEvent": methods.deleteRecurringEvent,
    }

    # Iterate through the function calls
    for call in function_calls:
        # Split the string to extract function name and arguments
        if call != "":
            parts = call.split("(")
            function_name = parts[0]
            arguments = parts[1].rstrip(")").split(", ")

        # Call the corresponding function with the provided arguments
        if function_name in functions:
            functions[function_name](*arguments)
        else:
            print(f"Function '{function_name}' not found.")
