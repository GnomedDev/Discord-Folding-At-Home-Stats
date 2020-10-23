import json
from configparser import ConfigParser
from datetime import datetime, timedelta
from inspect import cleandoc
from traceback import format_exception

import aiohttp
import discord
from discord.ext import commands, tasks

from utils import settings
from utils import basic

#//////////////////////////////////////////////////////
config = ConfigParser()
config.read("config.ini")
t = config["Main"]["Token"]
config_channel = config["Channels"]

BOT_PREFIX = "@"
#//////////////////////////////////////////////////////
activity = discord.Activity(name=config["Activity"]["name"], type=getattr(discord.ActivityType, config["Activity"]["type"]))
intents = discord.Intents(guilds=True, members=True, guild_messages=True)
status = getattr(discord.Status, config["Activity"]["status"])

bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents, status=status, activity=activity)
bot.channels = dict()
bot.trusted = basic.remove_chars(config["Main"]["trusted_ids"], "[", "]", "'").split(", ")

bot.load_extension("cogs.common")
bot.remove_command("help")
#//////////////////////////////////////////////////////
class Main(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def cog_unload(self):
        self.updater.cancel()
        self.save_files.cancel()

    @tasks.loop(seconds=60.0)
    async def save_files(self):
        try:    settings.save()
        except Exception as e:
            error = getattr(e, 'original', e)

            temp = f"```{''.join(traceback.format_exception(type(error), error, error.__traceback__))}```"
            if len(temp) >= 1900:
                with open("temp.txt", "w") as f:  f.write(temp)
                await self.bot.channels["errors"].send(file=discord.File("temp.txt"))
            else:
                await self.bot.channels["errors"].send(temp)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.embeds and message.channel.id in (749971061843558440, 764545844761591808) and str(message.author) == "GitHub#0000":
            print("Message is from a github webhook")
            if " new commit" in message.embeds[0].title:
                print("Message is a commit")
                update_for_main = message.embeds[0].title.startswith("[Discord-Folding-At-Home-Stats:master]") and self.bot.user.id == 565820959089754119
                update_for_dev = message.embeds[0].title.startswith("[Discord-Folding-At-Home-Stats:dev]") and self.bot.user.id == 705200761482510558
                cog_update = message.embeds[0].title.startswith("[Common-Cogs:master]")

                print (update_for_main, update_for_dev, cog_update, "\n===============================================")

                if update_for_main or update_for_dev:
                    await self.bot.channels['logs'].send(f"Detected new bot commit! Pulling changes")
                    call(['git', 'pull'])
                    print("===============================================")
                    await self.bot.channels['logs'].send("Restarting bot...")
                    await self.end(message)

                elif cog_update:
                    await self.bot.channels['logs'].send(f"Detected new cog commit! Pulling changes")
                    call(['git', 'submodule', 'update', '--recursive', '--remote'])
                    print("===============================================")
                    await self.bot.channels['logs'].send("Reloading cog...")

                    try:
                        self.bot.reload_extension("cogs.common")
                    except Exception as e:
                        await self.bot.channels['logs'].send(f'**`ERROR:`** {type(e).__name__} - {e}')
                    else:
                        await self.bot.channels['logs'].send('**`SUCCESS`**')

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.supportserver = self.bot.get_guild(int(config["Main"]["main_server"]))

        for channel_name in config_channel:
            channel_id = int(config_channel[channel_name])
            channel_object = self.bot.supportserver.get_channel(channel_id)
            self.bot.channels[channel_name] = channel_object

        try:
            self.updater.start()
            self.save_files.start()
        except RuntimeError: pass
        print(f"Started as {self.bot.user.name}!")
        await self.bot.channels["logs"].send("Started!")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        role = self.bot.supportserver.get_role(703307566654160969)
        await self.bot.channels["servers"].send(f"Just joined {guild.name}! I am now in {str(len(self.bot.guilds))} different servers!".replace("@", "@ "))

        try:
            if guild.owner_id in [member.id for member in self.bot.supportserver.members if not isinstance(member, NoneType)]:
                owner = self.bot.supportserver.get_member(guild.owner_id)
                await owner.add_roles(role)

                embed = discord.Embed(description=f"**Role Added:** {role.mention} to {owner.mention}\n**Reason:** Owner of {guild.name}")
                embed.set_author(name=f"{str(owner)} (ID {owner.id})", icon_url=owner.avatar_url)

                await self.bot.channels["logs"].send(embed=embed)
        except AttributeError:  pass

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self.bot.channels["servers"].send(f"Just left/got kicked from {str(guild.name)}. I am now in {str(len(self.bot.guilds))} servers".replace("@", "@ "))

    @commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True)
    @commands.command(aliases=["commands"])
    async def help(self, ctx):
        embed=discord.Embed(
            title="Folding At Home Stats Help!",
            description=cleandoc(f"""
                **@setup #textchannel -search/-number name/teamnumber**
                Sets the leaderboard up to the channel you specifiy. Use -search if you want to search for a team, or -number if you already have the team number!
                **@stats username**
                Gets the stats of a F@H Donor!

                **Universal Commands**
                @help: Shows this message
                @suggest *suggestion*: Suggests a new feature, reports a bug, or just tells me that I am cool :)
                @donate: Help improve {self.bot.user.name}'s development and hosting through Patreon
                @invite: Sends the instructions to invite {self.bot.user.name}!"""),
            url="https://www.discord.gg/zWPWwQC",
            color=0xfe6215)

        embed.set_thumbnail(url="https://foldingathome.org/wp-content/uploads/2016/09/folding-at-home-logo.png")
        embed.set_footer(text=f"Do you want to get support for {self.bot.user.name} or invite it to your own server? https://discord.gg/zWPWwQC")
        await ctx.send(embed=embed)

    @commands.bot_has_guild_permissions(read_messages=True, send_messages=True, embed_links=True)
    @commands.command()
    async def stats(self, ctx, *, donor: str):
        await ctx.channel.trigger_typing()
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://stats.foldingathome.org/api/donor/{donor}") as resp:
                if str(resp.status) != "404":   donor_json = await resp.json()
                else:   return await ctx.send("**Error:** Invalid Donor")

            teamstuff = str()
            for team in donor_json["teams"]:
                async with session.get(f"https://stats.foldingathome.org/api/team/{team['team']}") as resp:
                    team_json = await resp.json()

                teamstuff = f"""
                    {teamstuff}**Name:** {team["name"]}
                    **Contributed Credit** {team["credit"]:,}
                    **Total Team Credit:** {int(team_json["credit"]):,}
                    **Team Number:** {team["team"]}\n
                    """

        embed = discord.Embed(
            title=f"**Stats of {donor}**",
            description=cleandoc(f"""
                **Total Credit:** {int(donor_json["credit"]):,}
                **Total Work Units:** {int(donor_json["wus"]):,}
                **Overall Rank:** {int(donor_json["rank"]):,} out of {int(donor_json["total_users"]):,}

                **Teams**:
                {cleandoc(teamstuff)}"""),
            url=f"https://stats.foldingathome.org/donor/{donor}",
            color=0xfe6215)

        embed.set_thumbnail(url="https://foldingathome.org/wp-content/uploads/2016/09/folding-at-home-logo.png")
        embed.set_footer(text=f"Do you want to get support for {self.bot.user.name} or invite it to your own server? https://discord.gg/zWPWwQC")
        await ctx.send(embed=embed)

    @commands.has_permissions(administrator=True)
    @commands.bot_has_guild_permissions(read_messages=True, send_messages=True, embed_links=True)
    @commands.command()
    async def setup(self, ctx, channel : discord.TextChannel, search : str, *, name : str):
        await channel.trigger_typing()

        async with aiohttp.ClientSession() as session:
            if search.lower() == "-search":
                async with session.get(f"https://stats.foldingathome.org/api/teams?name={name}&search_type=exact") as resp:
                    firstjson = await resp.json()
                    try:    teamnumber = str(firstjson["results"][0]["team"])
                    except: return await ctx.send("**Error:** Invalid Team Name")
            else:   teamnumber = name

            async with session.get(f"https://stats.foldingathome.org/api/team/{teamnumber}") as resp:
                teamjson = await resp.json()

        number = 1
        message = str()
        total = teamjson["credit"]
        for donor in teamjson["donors"][:10]:
            message += f"**{number}. {donor['name']}:** {donor['credit']:,}\n"
            number += 1

        embed = discord.Embed(title=f"{teamjson['name']}'s Team Stats", url=f"https://stats.foldingathome.org/team/{teamnumber}", color=0xfe6215)
        embed.set_footer(text="Top 10 Leaderboard, made by Gnome!#6669! https://discord.gg/zWPWwQC")
        embed.set_thumbnail(url="https://foldingathome.org/wp-content/uploads/2016/09/folding-at-home-logo.png")

        embed.add_field(name="**Leaderboard**", value=message, inline=False)
        embed.add_field(name="Total", value=f"{int(total):,}", inline=True)
        embed.add_field(name="Team Number", value=teamnumber, inline=True)

        messagemade = await channel.send(embed=embed)

        settings.set(ctx.guild, "channel", messagemade.channel.id)
        settings.set(ctx.guild, "message", messagemade.id)
        settings.set(ctx.guild, "teamnumber", teamnumber)

    @commands.is_owner()
    @commands.command()
    async def forcesetup(self, ctx, channel : discord.TextChannel, search : str, *, name : str):
        await self.setup(ctx, channel, search, name)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if hasattr(ctx.command, 'on_error'):    return

        error = getattr(error, 'original', error)
        if isinstance(error, commands.NotOwner) or isinstance(error, commands.CommandNotFound):
            return

        elif isinstance(error, commands.BadArgument) or isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(f"Did you type the command right, {ctx.author.mention}?\nTry doing @help!")

        elif isinstance(error, commands.BotMissingPermissions):
            if "send_messages" in str(error.missing_perms):
                return await ctx.author.send("Sorry I could not complete this command as I don't have send messages permissions.")
            return await ctx.send(f"I am missing the permissions: {basic.remove_chars(str(error.missing_perms), '[', ']')}")

        first_part = f"{str(ctx.author)} caused an error with the message: {ctx.message.clean_content}"
        second_part = ''.join(format_exception(type(error), error, error.__traceback__))
        temp = f"{first_part}\n```{second_part}```"

        if len(temp) >= 1900:
            with open("temp.txt", "w") as f:    f.write(temp)
            await self.bot.channels["errors"].send(file=discord.File("temp.txt"))
        else:
            await self.bot.channels["errors"].send(temp)

    @tasks.loop(seconds=30.0)
    async def updater(self):
        async with aiohttp.ClientSession() as session:
            for guild in self.bot.guilds:
                channel = settings.get(guild, "channel")
                message = settings.get(guild, "message")
                teamnumber = settings.get(guild, "teamnumber")

                if (channel := self.bot.get_channel(int(channel))) is None: continue
                if (messagetoedit := await channel.fetch_message(int(message))) is None: continue

                async with session.get(f"https://stats.foldingathome.org/api/team/{teamnumber}") as resp:
                    teamjson = await resp.json()

                number = 1
                message = str()
                total = teamjson["credit"]
                for donor in teamjson["donors"][:10]:
                    message += f"**{number}. {donor['name']}:** {donor['credit']:,}\n"
                    number += 1

                embed = discord.Embed(title=f"{teamjson['name']}'s Team Stats", url=f"https://stats.foldingathome.org/team/{teamnumber}", color=0xfe6215)
                embed.set_footer(text="Top 10 Leaderboard, made by Gnome!#6669! https://discord.gg/zWPWwQC")
                embed.set_thumbnail(url="https://foldingathome.org/wp-content/uploads/2016/09/folding-at-home-logo.png")

                embed.add_field(name="**Leaderboard**", value=message, inline=False)
                embed.add_field(name="Total", value=f"{int(total):,}", inline=True)

                time_string = (datetime.now() + timedelta(hours=0)).strftime("%H:%M:%S")
                embed.add_field(name="Team Number", value=teamnumber, inline=True)
                embed.add_field(name="Last Updated (GMT)", value=time_string, inline=True)
                await messagetoedit.edit(embed=embed)
bot.add_cog(Main(bot))
bot.run(t)
