# Folding@Home Stats Bot

A Discord Bot to track Folding@Home Stats using Python and discord.py!

## Setup Guide:
### Easy:
- Invite the bot with [this invite](https://discordapp.com/api/oauth2/authorize?client_id=565820959089754119&permissions=84992&scope=bot)
- Run @setup <#channel> -search \<Team Name>

### Hard (Self Host):
- Make sure you have python 3.8 or above installed
- Make a bot account with [the Discord Developer Portal](https://discord.com/developers/applications/) and note down the token
- Toggle the `Server Members Intent` toggle in the portal
- Make sure you have a Discord server ready to be setup as a hub for Folding@Home Stats
- Run `git clone --recurse-submodules https://github.com/Gnome-py/Discord-Folding-At-Home-Stats`
- Run `python -m pip install -r requirements.txt`
- Run `python setup.py` and follow the instructions
- Run `python main.py`, and you should have your own instance of Folding@Home Stats running!