# -*- coding: utf-8 -*-
# !/usr/bin/env python3.5

"""

"""
import random
import time
from collections import defaultdict

import discord

from cogs.utils import comm, commons, prefs, scores
from cogs.utils.comm import logwithinfos
from cogs.utils.prefs import getPref
from .commons import _

logger = commons.logger
bot = commons.bot


async def allCanardsGo():
    for canard in commons.ducks_spawned:
        try:
            await canard["channel"].send(_(random.choice(commons.canards_bye), language=getPref(canard["channel"].guild, "language")))
            await logwithinfos(canard["channel"], None, "Force-leaving of duck " + str(canard))
        except:
            await logwithinfos(canard["channel"], None, "Force-leaving of duck FAILED " + str(canard))
            logger.exception("Here is why : ")


async def planifie(channel_obj: discord.Channel = None):
    now = int(time.time())
    thisDay = now - (now % 86400)
    seconds_left = 86400 - (now - thisDay)
    multiplicator = round(seconds_left / 86400, 5)
    if not channel_obj:
        logger.debug("Replanning")
        commons.bread = defaultdict(int)
        planification_ = {}
        if multiplicator == 0:
            multiplicator = 1
        servers = prefs.JSONloadFromDisk("channels.json")
        for server_ in list(servers.keys()):
            guild = bot.get_guild(str(server_))
            if not guild:
                logger.debug("Non-existant server : " + str(server_))
                servers.pop(server_)
                scores.delServerPlayers(sid=server_)

            elif not "channels" in servers[guild.id]:
                await comm.logwithinfos(guild.default_channel, log_str="Server not configured : " + guild.id)
                try:
                    await guild.send("The bot is not configured properly, please check the config or contact Eyesofcreeper#4758 | https://discord.gg/2BksEkV")
                    await comm.logwithinfos(guild.default_channel, log_str="Unconfigured message sent...")
                except:
                    await comm.logwithinfos(guild.default_channel, log_str="Error sending the unconfigured message to the default channel on the server.")

            else:
                for channel_ in servers[guild.id]["channels"]:
                    channel = guild.get_channel(str(channel_))
                    if channel:
                        permissions = channel.permissions_for(guild.me)
                        if permissions.read_messages and permissions.send_messages:
                            # logger.debug("Adding channel : {id} ({ducks_per_day} c/j)".format(**{
                            #    "id"           : channel.id,
                            #    "ducks_per_day": prefs.getPref(server, "ducks_per_day")
                            # }))
                            planification_[channel] = round(prefs.getPref(guild, "ducks_per_day") * multiplicator)
                        else:
                            await comm.logwithinfos(channel, log_str="Error adding channel to planification : no read/write permissions!")
                    else:
                        pass
        commons.ducks_planned = planification_  # {"channel":[time objects]}
        prefs.JSONsaveToDisk(servers, "channels.json")

    else:
        commons.bread[channel_obj] = 0
        permissions = channel_obj.permissions_for(channel_obj.guild.me)
        if permissions.read_messages and permissions.send_messages:
            pass
        else:
            await comm.logwithinfos(channel_obj, log_str="Error adding channel to planification : no read/write permissions!")
        commons.ducks_planned[channel_obj] = round(prefs.getPref(channel_obj.guild, "ducks_per_day") * multiplicator)


async def spawn_duck(duck):
    servers = prefs.JSONloadFromDisk("channels.json", default="{}")
    try:
        if servers[duck["channel"].guild.id]["detecteur"].get(duck["channel"].id, False):
            for playerid in servers[duck["channel"].guild.id]["detecteur"][duck["channel"].id]:
                player = discord.utils.get(duck["channel"].guild.members, id=playerid)
                try:
                    await player.send(_("There is a duck on #{channel}", prefs.getPref(duck["channel"].guild, "language")).format(**{
                        "channel": duck["channel"].name
                    }))
                    await comm.logwithinfos(duck["channel"], player, "Sending a duck notification")
                except:
                    await comm.logwithinfos(duck["channel"], player, "Error sending the duck notification")
                    pass

            servers[duck["channel"].guild.id]["detecteur"].pop(duck["channel"].id)
            prefs.JSONsaveToDisk(servers, "channels.json")
    except KeyError:
        pass

    chance = random.randint(0, 100)
    if chance <= prefs.getPref(duck["channel"].guild, "super_ducks_chance"):
        minl = prefs.getPref(duck["channel"].guild, "super_ducks_minlife")
        maxl = prefs.getPref(duck["channel"].guild, "super_ducks_maxlife")
        if minl != maxl:
            if maxl < minl:
                maxl, minl = minl, maxl
                await comm.logwithinfos(duck["channel"], None, "Minl and maxl swapped")
            life = random.randint(minl, maxl)
        else:
            life = minl

        duck["isSC"] = True
        duck["SCvie"] = life
        duck["level"] = life
    else:
        duck["isSC"] = False
        duck["level"] = 1
        duck["SCvie"] = 1

    await comm.logwithinfos(duck["channel"], None, "New duck : " + str(duck))
    duck["time"] = time.time()
    if prefs.getPref(duck["channel"].guild, "emoji_ducks"):
        corps = prefs.getPref(duck["channel"].guild, "emoji_used") + " < "
    else:
        corps = random.choice(commons.canards_trace) + "  " + random.choice(commons.canards_portrait) + "  "

    if prefs.getPref(duck["channel"].guild, "randomize_ducks"):
        canard_str = corps + _(random.choice(commons.canards_cri), language=prefs.getPref(duck["channel"].guild, "language"))
    else:
        canard_str = corps + "QUAACK"
    try:
        await duck["channel"].send(canard_str, tts=prefs.getPref(duck["channel"].guild, "tts_ducks"))
    except:
        pass
    commons.n_ducks_spawned += 1
    commons.ducks_spawned.append(duck)


async def del_channel(channel):
    servers = prefs.JSONloadFromDisk("channels.json")
    try:
        if channel.id in servers[channel.guild.id]["channels"]:
            await comm.logwithinfos(channel, log_str="Deleting channel {name} | {id} from the json file...".format(**{
                "id"  : channel.id,
                "name": channel.name
            }))
            servers[channel.guild.id]["channels"].remove(channel.id)
            prefs.JSONsaveToDisk(servers, "channels.json")
            try:
                commons.ducks_planned.pop(channel)  # Remove from planification
                pass
            except:
                pass
            for duck in commons.ducks_spawned[:]:
                if duck["channel"] == channel:
                    commons.ducks_spawned.remove(duck)
                    commons.n_ducks_flew += 1
    except KeyError:
        pass
