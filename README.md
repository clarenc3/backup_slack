# Slack backup for T2K-related project
Runs on MaCh3 and NUISANCE Slack channels<br />

Backs up channel history from public and private channels and pulls in the attachements<br />

# How to
1) Install slacker from github: https://github.com/os/slacker<br />
2) Get a legacy API token from Slack: https://api.slack.com/custom-integrations/legacy-tokens<br />
3) Modify the variables in the script<br />
  e.g. the API key, bot username, channel to post to, where to backup<br />

# Building further
All API calls are at https://api.slack.com/methods<br />
Slacker's implementation is found in slacker/__init__.py<br />
