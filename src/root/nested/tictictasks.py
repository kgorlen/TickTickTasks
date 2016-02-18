'''
Convert Todoist .json export file to Tick Tick .csv backup/import file

Created on Feb 12, 2016

@author: Keith gorlen@comcast.net


Todist export "everything" to .json: https://eclectide.com/todoist-export/

'''

import json
import csv
import re
from datetime import date, datetime
from dateutil import tz
from dateutil.parser import parse
from pprint import pprint

DIRECTORY = '//NAS0/Keith/Downloads/todoist/'
INFILE = 'todoist.json'
LOCAL_TZNAME = 'America/Los_Angeles'

UTC_ZONE = tz.gettz('UTC')
LOCAL_ZONE = tz.gettz(LOCAL_TZNAME)
TODAY = date.today().isoformat()
RE_OUTLOOKLINK = re.compile(r'.*(?P<link>\[\[outlook=[^,]+,\s*(?P<title>.*)\]\])', re.IGNORECASE)
RE_THUNDERLINK = re.compile(r'.*(?P<link>thunderlink://.*)', re.IGNORECASE)
RE_INTERVAL = re.compile(r'\s*(?P<tag>after|every)\s+(?:(?P<interval>\d+)\s+)?(?P<freq>day|week|month|year)', re.IGNORECASE)
RE_EVERY_MMDD = re.compile(r'\s*every\s+(?P<month>\d+)\s*[/-]\s*(?P<day>\d+)', re.IGNORECASE)
RE_EVERY_MMMDD = re.compile(r'\s*every\s+(?P<month>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+(?P<day>\d+)', re.IGNORECASE)
RE_EVERY_DDMMM = re.compile(r'\s*every\s+(?P<day>\d+)\s+(?P<month>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', re.IGNORECASE)
RE_EVERY_NTH_DAYOFWEEK = re.compile(r'\s*every\s+(?P<ord>[1-5])(?:st|nd|rd|th)?\s+(?P<dayOfWeek>su|mo|tu|we|th|fr|sa)', re.IGNORECASE)
RE_EVERY_DD = re.compile(r'\s*every\s+(?P<day>\d+)', re.IGNORECASE)
#RE_ORDINALS = r'((?:2?(?:1st|2nd|3rd|[04-9]th))|1[0-9]th|30th|31st)'
MMM_TO_MM = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}

def parseRecurrence(rstring) :
    '''
    Convert Todoist free-form recurring task strings to RFC 2445 iCalendar recurrence rules
    
    FREQ=[DAILY|WEEKLY|MONTHLY|YEARLY]
    INTERVAL=n
    BYDAY={n}[SU|MO|TU|WE|TH|FR|SA]
    BYMONTHDAY=n
    BYMONTH=n
    WKST=[SU|MO|TU|WE|TH|FR|SA]
    UNTIL=YYYYMMDD
 
    Recurring after: FREQ=<freq>;INTERVAL=n
    Recurring every: FREQ=<freq>;INTERVAL=n;BYDAY=n<dayOfWeek>
    Recurring every: FREQ=<freq>;INTERVAL=n;BYMONTH=<month>;BYMONTHDAY=n
    '''    
    rrule = ''
    if (rstring) :
        mob = RE_INTERVAL.match(rstring)
        if (mob) :
            freq = mob.group('freq').upper()
            if (freq == 'DAY') : freq = 'DAI'
            interval = mob.group('interval')
            if (not interval) : interval = 1
            rrule = 'FREQ=' + freq + 'LY;INTERVAL=' + str(interval)
            return rrule.upper()

        mob = RE_EVERY_MMDD.match(rstring)
        if (mob) :
            rrule = 'FREQ=YEARLY;BYMONTH=' + mob.group('month') + ';BYMONTHDAY=' + mob.group('day')
            return rrule.upper()

        mob = RE_EVERY_MMMDD.match(rstring) or RE_EVERY_DDMMM.match(rstring)
        if (mob) :
            mm = MMM_TO_MM[mob.group('month').lower()]
            rrule = 'FREQ=YEARLY;BYMONTH=' + str(mm) + ';BYMONTHDAY=' + mob.group('day')
            return rrule.upper()
        
        mob = RE_EVERY_NTH_DAYOFWEEK.match(rstring)
        if mob :
            rrule = 'FREQ=MONTHLY;INTERVAL=1;BYDAY=' + str(mob.group('ord')) + mob.group('dayOfWeek')
            return rrule.upper()

        mob = RE_EVERY_DD.match(rstring)        
        if mob :
            rrule = 'FREQ=MONTHLY;INTERVAL=1;BYMONTHDAY=' + str(mob.group('day'))
            return rrule.upper()
    return ''


with open(DIRECTORY+INFILE) as data_file :
    data = json.load(data_file)   
    
notes = {}      # dict of array of note dicts, keyed by task id
for i in data['Notes'] :
    if (i['item_id'] not in notes) : notes[i['item_id']] = []
    notes[i['item_id']].append(i)
# pprint(notes)
    
project = {}    # dict of project dicts, keyed by project id
for i in data['Projects'] :
    project[i['id']] = i
# pprint(project)

tasks = {}       # dict of array of task dicts, keyed by project name
for i in data['Items'] :
    projectName = project[i['project_id']]['name']
    if (projectName not in tasks) : tasks[projectName] = []
    tasks[projectName].append(i)

for projectName in sorted(tasks.keys()) :
    with open(DIRECTORY+'TickTick/'+TODAY+' '+projectName+'.csv', 'w',\
              encoding='utf8', newline='') as csvfile :

# Tick Tick .csv header
        csvfile.write('"Date: ' + TODAY + '+0000"\n')
        csvfile.write('"Version: 2.0"\n')
        csvfile.write('"Status: \n0 Normal\n1 Completed\n2 Archived"\n')
        output = csv.writer(csvfile, quoting=csv.QUOTE_ALL, lineterminator='\n')
        output.writerow(["List Name","Title","Content","Is Checklist","Due Date","Reminder","Repeat","Priority","Status","Completed Time","Order","Timezone","Is All Day"])
    
        order = 1 - len(tasks[projectName])
        for task in sorted(tasks[projectName], key=lambda k: parse(k['date_added']).isoformat()) :
            row = []
    
    # List Name: Todoist project name
            row.append(projectName)
    
    # Title: Todoist task name
            taskName = task['content']
            mob = re.match(RE_OUTLOOKLINK, taskName)
            if (mob) :  # Move outlook email link to note
                if (task['id'] not in notes) : notes[task['id']] = []
                notes[task['id']].append( {'content': mob.group('link'), 'posted': task['date_added'] } )
                taskName = mob.group('title')
            row.append(taskName)
    
    # Content: Todoist notes
            note = []
            if (task['id'] in notes) :
                notesByDate = {}
                for n in notes[task['id']] :
                    mob = re.match(RE_THUNDERLINK, n['content'])
                    if (mob) :  # Move ThunderLink to task name
                        row[1] += '\r' + mob.group('link')
                    else :
                        posted = parse(n['posted']).replace(tzinfo=UTC_ZONE).astimezone(LOCAL_ZONE)
                        n['posted_datetime'] = posted
                        notesByDate[posted] = n
                for n in sorted(notesByDate.keys()) :
                    note.append(notesByDate[n]['posted_datetime'].strftime('%b %d %Y %I:%M %p') + '\r')
                    note.append(re.sub(r'^[\s\r]*(.*?)\r*$', \
                                   '\g<1>\r---\r', \
                                   notesByDate[n]['content'].replace('\n','\r'), \
                                   flags=re.DOTALL))
            row.append(''.join(note))
    
    # Is Checklist: Todoist doesn't support checklists
            row.append('N')
    
    # Due Date (UTC)
            if (task['due_date_utc']) :
                row.append(parse(task['due_date_utc']).isoformat().replace('+00:00', '+0000'))
            else : row.append('')
    
    # Reminder: To be implemented
            row.append('')
    
    # Repeat: (RFC 2445 iCalendar recurrence rule)
            rstring = task['date_string']
            rrule = ''
            if (rstring) :
                rrule = parseRecurrence(rstring)
                if (re.match(r'.*(?:after|every)', rstring, re.IGNORECASE)) :
                    print(projectName + ':' + taskName + ': ' + rstring + '-->' + rrule)
            row.append(rrule)
    
    # Priority
            row.append(['0', '1', '3', '5'][task['priority']-1])
    
    # Status: Always Normal
            row.append('0')
    
    # Completed Time: No completion time
            row.append('')
    
    # Order: (... -3, -2, -1, 0) << 38
            row.append(str(order << 38))
            order +=1
    
    # Timezone
            row.append(LOCAL_TZNAME)
    
    # Is All Day: true if due_date
    #         if (task['due_date']): row.append('true')
    #         else: row.append('')
            row.append('')
    
            output.writerow(row)
    
