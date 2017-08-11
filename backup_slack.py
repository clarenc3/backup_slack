#!/usr/bin/python

# Slacker import
from slacker import Slacker
import os
import operator
import datetime
import time
import re
# Neede for exit
import sys
# Needed to pull files from Slack
import urllib2

# The Slack legacy API key
api_key = "YOUR_API_KEY"
# Make the slacker object which we use for the API
slack = Slacker(api_key)

# The time pattern we want
time_pattern = "%Y-%m-%d_%H:%M:%S"
# Get the month for today
month = datetime.datetime.today().strftime('%Y_%m')
# The logging directory
logfile_dir = "YOUR_POSTING_DIRECTORY/%s"%(month)
if not os.path.exists(logfile_dir):
  os.makedirs(logfile_dir)

# User name of bot
user="USER"
# Icon of bot
icon="ICON_POSTER"
# The "header" for the Slack message, akak pretex
subject="MESSAGE"


# A message class which we loop over in main
class Message:

  def __init__(self, message, users):

    # Get the text of the message
    self.text = message["text"]
    # Get the time stamp
    self.timestamp, self.msg_id = map(int, message["ts"].split("."))
    # Set the time
    self.time_formatted = datetime.datetime.fromtimestamp(self.timestamp).strftime(time_pattern)

    # Try setting the subtype
    try:
      self.subtype = message["subtype"]
    except KeyError:
      self.subtype = None

    # Get some file shares
    if self.subtype == "file_share":
      self.link = message["file"]["url_private"]
      self.linkname = message["file"]["name"]
      extension = os.path.splitext(self.linkname)[1]
      self.linkname = (os.path.splitext(self.linkname)[0]+"_"+self.time_formatted+extension).replace(" ", "_")

    else:
      self.link = None
      self.linkname = None

    # Naming of messages is wildly inconsistent...
    try:
      self.uid = message["user"]
      self.username = users[self.uid]
    # If something goes wrong with our key
    except KeyError:
      try:
        # Maybe this logged as a bot
        self.uid      = message["bot_id"]
        self.username = message["username"]
        # The logging bot (running this program) formats in a special way
        if self.username == user:
          self.text     = message["attachments"][0]["pretext"]+message["attachments"][0]["text"]
      except KeyError:
        # or maybe this was a comment of a comment
        try:
          self.uid      = message["comment"]["user"]
          self.username = users[self.uid]
        except KeyError:
          # or maybe this was a comment of a attachment
          try:
            self.uid      = message["attachements"]["bot_id"]
            self.username = users["username"]
          except KeyError:
            self.uid = message["bot_id"]
            # The official GitHub app seems to post messages, uhm, differently
            if self.uid == "B1QTP89JT":
              self.username = "GitHub"
              altmessage = ""
              # GitHub can't deal with Leila's name or one of Kirsty's commit containing \xef
              try:
                altmessage = message["attachments"][0]["pretext"]
              except UnicodeEncodeError:
                altmessage = message["attachments"][0]["pretext"].encode('utf-8')
              except KeyError:
                pass
              try:
                altmessage += message["attachments"][0]["text"]
              except UnicodeEncodeError:
                altmessage += message["attachments"][0]["text"].encode('utf-8')
              except KeyError:
                pass

              self.text = altmessage
            else:
              self.username = "Unknown bot"


  def AsLine(self, replacement_dicts):
    l = u"[%s]\n   %s: %s"%(self.time_formatted, self.username.ljust(17), self.text)
    for d in replacement_dicts:
      for k, v in d.iteritems():
        l = l.replace(k, v)
    return l


# The main function to run
def main():

  # Get the users, channels and private channels
  users = GetUsers()
  channels = GetChannels()
  priv_channels = GetChannelsPrivate()

  # The channel that posts the results of the logger
  log_channel_id = "POSTING_CHANNEL"

  #############################
  # Do the public channels
  n_new_lines = dict([(c,0) for c in channels.iterkeys()])
  n_new_attach = dict([(c,0) for c in channels.iterkeys()])
  for chan_id, chan_name in channels.iteritems():
    logfile_name = logfile_dir+"/%s_log_%s.txt"%(chan_name, month)
    last_datetime = get_last_message_datetime(logfile_name)
    last_timestamp = time.mktime(last_datetime.timetuple())

    raw_messages = GetFullMessages(chan_id, chan_name)
    messages = [Message(m, users) for m in raw_messages]

    # Get rid of messages which are too old
    messages = [m for m in messages if m.timestamp > last_timestamp]
    messages.sort(key=lambda x: x.timestamp)

    # Find the logging channels id (not name!)
    if chan_name == log_channel_id:
      log_channel_id = chan_id

    # Open the file to append to and write the log
    with open(logfile_name,"a") as f:
      for m in messages:
        line = m.AsLine([channels, users])+"\n"
        f.write(line.encode('utf8'))
        n_new_lines[chan_id] += 1

    # Get the attachments in the messages
    for m in messages:
      if m.link != None:
      # Make the directory
        logfile_img = logfile_name.strip(".txt")+"_img"
        if not os.path.exists(logfile_img):
          os.makedirs(logfile_img)

        filename = logfile_img+"/"+m.linkname
        # Make the OAuth request using the slack key
        req = urllib2.Request(m.link, None, {'Authorization' : 'Bearer '+api_key})
        response = urllib2.urlopen(req)
        file = open(filename, 'wb')
        file.write(response.read())
        file.close()
        n_new_attach[chan_id] += 1

  #############################
  # Now do the private channels
  n_priv_new_lines = dict([(c,0) for c in priv_channels.iterkeys()])
  n_new_attach_priv = dict([(c,0) for c in priv_channels.iterkeys()])
  for chan_id, chan_name in priv_channels.iteritems():
    logfile_name = logfile_dir+"/%s_log_%s.txt"%(chan_name,month)
    last_datetime = get_last_message_datetime(logfile_name)
    last_timestamp = time.mktime(last_datetime.timetuple())

    raw_messages = GetFullMessages(chan_id, chan_name)
    messages = [Message(m, users) for m in raw_messages]

    # Get rid of messages which are too old
    messages = [m for m in messages if m.timestamp > last_timestamp]
    messages.sort(key=lambda x: x.timestamp)

    if chan_name == log_channel_id:
      log_channel_id = chan_id

    # Open the file to append to and write the log
    with open(logfile_name,"a") as f:
      for m in messages:
        line = m.AsLine([priv_channels, users])+"\n"
        f.write(line.encode('utf8'))
        n_priv_new_lines[chan_id] += 1

    # Get the attachments in the private messages
    for m in messages:
      if m.link != None:
      # Make the directory
        logfile_img = logfile_name.strip(".txt")+"_img"
        if not os.path.exists(logfile_img):
          os.makedirs(logfile_img)

        filename = logfile_img+"/"+m.linkname
        # Make the OAuth request
        req = urllib2.Request(m.link, None, {'Authorization' : 'Bearer '+api_key})
        response = urllib2.urlopen(req)
        file = open(filename, 'wb')
        file.write(response.read())
        file.close()
        n_new_attach_priv[chan_id] += 1

  # The body we will use to send to Slack
  body = ""

  if log_channel_id is not None:
    for chan_id,n in n_new_lines.iteritems():
      output = "Wrote "+`n`+" messages for #"+channels[chan_id]
      body += output+"\n"
      print output

  if log_channel_id is not None:
    for chan_id,n in n_priv_new_lines.iteritems():
      output = "Wrote "+`n`+" messages for #"+priv_channels[chan_id]
      body += output+"\n"
      print output


  slack.chat.post_message(
      channel=log_channel_id,
      as_user=False,
      username=user,
      icon_url=icon,
      attachments=[{"pretext": subject, 
        "fallback": subject,
        "color": "#36a64f",
        "footer": user,
        "text": body}])

  return

# Get the last logger message date and time
def get_last_message_datetime(logfile_name):
  # Open the logfile that might already be written
  try:
    f = open(logfile_name, "r")
  except IOError:
    return datetime.datetime.fromtimestamp(0)

  lines = reversed([l for l in f])
  f.close()
  matcher = re.compile(r"^\[(\d\d\d\d-\d\d-\d\d\_\d\d:\d\d:\d\d)]") # the date-time pattern above
  last_datetime = datetime.datetime.fromtimestamp(0)
  for l in lines:
    m = matcher.search(l)
    if m is None: continue
    last_time_formatted = m.group(1)
    last_datetime = datetime.datetime.strptime(last_time_formatted, time_pattern)
    break
  return last_datetime

# Get a dict of users for a given slack
def GetUsers():
  Users = dict()
  l = slack.users.list().body["members"]
  for u in l:
    Users[u["id"]] = u["name"]
  return Users

# Get a dict of channels for a given slack
def GetChannels():
  Channels = dict()
  l = slack.channels.list().body["channels"]
  for c in l:
    Channels[c["id"]] = c["name"]
  return Channels

# Get a dict of private channels for a given slack
def GetChannelsPrivate():
  Priv_Channels = dict()
  l = slack.groups.list().body["groups"]
  for c in l:
    Priv_Channels[c["id"]] = c["name"]
  return Priv_Channels

# Get a full list of messages from Slack
def GetFullMessages(chan_id, chan_name):

  # Get the last 1000 messages (maximum we can get from Slack at one time)
  resp = slack.groups.history(chan_id, count=1000, inclusive=True)
  raw_messages = resp.body["messages"]

  # This is true if there are more messages we can get
  has_more = resp.body["has_more"]
  while has_more:
    # Get the timestamp for the earliest message we got in previous iteration
    timestamp = resp.body["messages"][-1]["ts"]
    # Make another request for the next messages
    resp = slack.groups.history(chan_id, count=1000, inclusive=True, latest=timestamp)
    # Prepend our older messages
    raw_messages = resp.body["messages"] + raw_messages
    # Check if we still have more
    has_more = resp.body["has_more"]

  return raw_messages

# The main we run
if __name__=="__main__":
  main()

