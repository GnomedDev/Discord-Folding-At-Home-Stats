import json

from utils.basic import get_value

with open("settings.json") as f:    settings = json.load(f)

default_settings = {"channel": 0, "message": 0, "teamnumber": 260950}

def save():
    with open("settings.json", "w") as f:    json.dump(settings, f)

def remove(guild):
    settings.pop(str(guild.id), None)

def cleanup(guild_id_list):
    for guild_id in settings.copy():
        if guild_id not in guild_id_list:
            del settings[guild_id]
            continue

        for key, value in settings[guild_id].copy().items():
            if key not in default_settings or value == default_settings[key]:
                del settings[guild_id][key]

        if settings[guild_id] == dict():
            del settings[guild_id]

def get(guild, setting):
    return get_value(settings, str(guild.id), setting, default_value=default_settings[setting])

def set(guild, setting, value):
    guild = str(guild.id)

    if guild in settings:
        if value == default_settings[setting] and setting in settings[guild]:
            del settings[guild][setting]
            return

        if settings[guild] == dict():
            del settings[guild]
            return
    else:
        settings[guild] = dict()

    settings[guild][setting] = value
