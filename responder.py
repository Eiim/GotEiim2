import asyncio
import datetime
import discord
import numpy as np
import os
import pandas as pd
import random
import re
import sqlite3
import time
import urllib.request
import random
import sched
import math
import threading
import functools
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")

# Reminder database
conRem = sqlite3.connect("reminders.db")
curRem = conRem.cursor()

# Set datetime adapter/covnerter (converter may not be necessary)
def adapt_datetime_epoch(val):
	"""Adapt datetime.datetime to Unix timestamp."""
	return int(val.timestamp())
sqlite3.register_adapter(datetime.datetime, adapt_datetime_epoch)

def convert_timestamp(val):
	"""Convert Unix epoch timestamp to datetime.datetime object."""
	return datetime.datetime.fromtimestamp(int(val))
sqlite3.register_converter("timestamp", convert_timestamp)

# Pycord stuff begins here
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

# Stopwords from Snowball
stopwds = ["i","me","my","myself","we","our","ours","ourselves","you","your","yours","yourself","yourselves","he","him","his","himself","she","her","hers","herself","it","its","itself","they","them","their","theirs","themselves","what","which","who","whom","this","that","these","those","am","is","are","was","were","be","been","being","have","has","had","having","do","does","did","doing","would","should","could","ought","i'm","you're","he's","she's","it's","we're","they're","i've","you've","we've","they've","i'd","you'd","he'd","she'd","we'd","they'd","i'll","you'll","he'll","she'll","we'll","they'll","isn't","aren't","wasn't","weren't","hasn't","haven't","hadn't","doesn't","don't","didn't","won't","wouldn't","shan't","shouldn't","can't","cannot","couldn't","mustn't","let's","that's","who's","what's","here's","there's","when's","where's","why's","how's","a","an","the","and","but","if","or","because","as","until","while","of","at","by","for","with","about","against","between","into","through","during","before","after","above","below","to","from","up","down","in","out","on","off","over","under","again","further","then","once","here","there","when","where","why","how","all","any","both","each","few","more","most","other","some","such","no","nor","not","only","own","same","so","than","too","very","will"]

helptext = """GotEiim2 Help:
* `$help`: Get help for GotEiim2
  * format: `$help`
* `$topwords`: Get the most-used words compared to their overall usage in English, filtered by a server, channel, or user.
  * format: `$topwords [category] [specifier]` or `$topwords [specifier]`
    * `category`: One of "server", "channel", or "user". Optional, defaults to "server".
    * `specifier`: A snowflake ID or mention of the server, channel, or user to filter on. Optional, defaults to the server/channel the message is sent in or the user who sent it. If `category` is excluded, this must be a user or channel mention.
* `$remindme`: Get a random reminder of something you wanted to be reminded of
  * format: `$remindme`
* `$setreminder`: Manually set a reminder for a message
  * format: `$setreminder [message]`
    * `message`: A link to a message. Alternatively, the command can be sent in a reply to the the message.
* `$remindstats`: Get stats of your reminder messages
  * format: `$remindstats`
* `$subreminders`: Subscribe to random (approximately weekly) automated reminders
  * format: `$subreminders`
* `$unsubreminders`: Unsubscribe from automated reminders
  * format: `$unsubreminders`
"""

remBot = []
remOrig = []

# Scheduler for automated reminders
s = sched.scheduler(time.time, time.sleep)
schedEvents = {}

# Async wrapper generator for scheduler
def make_wrapper(*args, **kwargs):
	return lambda: asyncio.get_event_loop().create_task(async_task(*args, **kwargs))

def schedule_coro(loop, coro_fn, *args, **kwargs):
	@functools.wraps(coro_fn)
	def _runner():
		logging.debug("[sched] fired %s%r", coro_fn.__name__, args)
		try:
			asyncio.run_coroutine_threadsafe(coro_fn(*args, **kwargs), loop)
		except Exception:
			logging.exception("[sched] %s crashed", coro_fn.__name__)
	return _runner

def getReminder(author, guild, timestamp, settime):
	curRem.execute("SELECT Snowflake, Channel_ID, Created, Last_Reminded, Snooze, Status FROM reminders WHERE Author_ID = ? AND Server_ID = ?", (author, guild))
	rems = curRem.fetchall()
	openRem = [r for r in rems if r[5] in ["New", "Open"]]
	n = len(openRem)
	if n == 0:
		return 0

	# Snooze penalty — exponential so high snooze values are near-zero weight
	# snooze=0 -> 1.0, snooze=2 -> ~0.37, snooze=5 -> ~0.082, snooze=10 -> ~0.0067
	snooze_weight = np.array([math.exp(-r[4] * 0.5) for r in openRem])

	# Recency weight — rank by Last_Reminded, most recent gets near-zero weight
	# Uses rank rather than raw timestamps to avoid issues with bunched values
	if n > 1:
		remind_ranks = np.argsort(np.argsort([r[3] for r in openRem], kind="mergesort"))
		# oldest=0, most recent=n-1; invert and normalise so oldest->1, newest->~0
		recency_weight = (n - 1 - remind_ranks) / (n - 1)
	else:
		recency_weight = np.array([1.0])

	# Creation date nudge — newer reminders score slightly higher
	if n > 1:
		create_ranks = np.argsort(np.argsort([r[2] for r in openRem], kind="mergesort"))
		create_weight = create_ranks / (n - 1)  # oldest->0, newest->1
	else:
		create_weight = np.array([1.0])

	# Combine: recency is primary, creation is a more gentle nudge, snooze gates everything
	score = snooze_weight * (recency_weight + 0.33 * create_weight)

	if max(score) <= 0:
		score = np.ones(n)  # fallback: all weights collapsed, choose randomly

	picked = random.choices(openRem, weights=score, k=1)[0]
	if settime:
		curRem.execute("UPDATE reminders SET Last_Reminded = ?, Status = 'Open' WHERE Snowflake = ?", (timestamp, picked[0]))
	curRem.execute("UPDATE reminders SET Snooze = Snooze - 1 WHERE Snooze > 0")
	conRem.commit()
	return (picked[0], picked[1])

async def sendReminder(author, channel, timestamp):
	r = getReminder(author.id, channel.guild.id, timestamp, True)
	if r == 0:
		await channel.send("No open reminders left for <@"+str(author.id)+">!")
		return
	remMsgChl = await channel.guild.fetch_channel(r[1])
	remMsg = await remMsgChl.fetch_message(r[0])
	newMsg = await channel.send("Reminding <@"+str(author.id)+">!\n"+remMsg.jump_url+"\n✅ done  ❎ invalid  💤 snooze  ⏭ next")
	remBot.append(newMsg.id)
	remOrig.append(r[0])
	asyncio.create_task(newMsg.add_reaction("✅"))
	asyncio.create_task(newMsg.add_reaction("❎"))
	asyncio.create_task(newMsg.add_reaction("💤"))
	asyncio.create_task(newMsg.add_reaction("⏭"))

async def sendRemindStats(author, channel):
	curRem.execute("SELECT Snooze, Status FROM reminders WHERE Author_ID = ? AND Server_ID = ?", (author.id, channel.guild.id))
	rems = curRem.fetchall()
	statuses = [r[1] for r in rems]
	snoozed = sum([1 if r[0] > 0 else 0 for r in rems])
	newRems = sum([1 if s == "New" else 0 for s in statuses])
	openRems = sum([1 if s == "Open" else 0 for s in statuses])
	doneRems = sum([1 if s == "Done" else 0 for s in statuses])
	invalidRems = sum([1 if s == "Invalid" else 0 for s in statuses])
	await channel.send("<@"+str(author.id)+"> has "+str(len(rems))+" reminders (" +
					str(newRems)+" new, " +
					str(openRems)+" open, " +
					str(doneRems)+" done, " +
					str(invalidRems)+" invalid, " +
					str(snoozed)+" snoozed)")

async def checkReminder(user, server, schedTime):
	print("checking rem...")
	curRem.execute("SELECT Last_Reminded FROM subscriptions WHERE User_ID = ? AND Server_ID = ?", (user, server))
	lastTime = curRem.fetchall()[0][0]
	nowTime = int(time.time())
	timeDelta = (nowTime - lastTime) / 3600
	print(timeDelta)
	if random.random() < (timeDelta / 336)**8: # 336 hours is 14 days, 8 is selected to make average about a week
		curRem.execute("UPDATE subscriptions SET Last_Reminded = ? WHERE User_ID = ? AND Server_ID = ?", (nowTime, user, server))
		conRem.commit()
		await sendReminder(user, client.get_guild(server).get_channel_or_thread(1353174170778734632), nowTime) # semi-temporarily hard-code channel ID
	schedEvents[user] = s.enterabs(schedTime + 3600, 10, lambda *a: asyncio.create_task(checkReminder(user, server, schedTime + 3600)))

async def setReminder(message):
	commandparts = message.content.split()
	print(commandparts)
	remMsg = None
	if len(commandparts) < 2 and message.reference is not None:
		remMsg = message.reference.resolved
	else:
		ids = re.match(r"https?:\/\/discord.com\/channels\/(\d+)/(\d+)/(\d+)", commandparts[1])
		if ids is not None:
			print(ids.groups())
			remMsg = await client.get_guild(int(ids.group(1))).get_channel_or_thread(int(ids.group(2))).fetch_message(int(ids.group(3)))
	if remMsg is None:
		await message.reply("Can't figure out what message you want to set a reminder for!")
		return
	if remMsg.author.id != message.author.id:
		await message.reply("You can only set a reminder for your own messages!")
		return
	curRem.execute("INSERT INTO reminders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (remMsg.id, remMsg.author.name, remMsg.author.id, remMsg.channel.id, remMsg.guild.id, remMsg.created_at, 0, 0, "New"))
	conRem.commit()
	await message.add_reaction("👍")

async def subscribeReminders(message):
	curRem.execute("SELECT Last_Reminded FROM subscriptions WHERE User_ID = ? AND Server_ID = ?", (message.author.id, message.guild.id))
	existingSubs = curRem.fetchall()
	if len(existingSubs) > 0:
		await message.reply("You're already subscribed!")
		return
	curRem.execute("INSERT INTO subscriptions VALUES (?, ?, ?, ?)", (message.author.id, message.guild.id, int(time.time()), int(time.time())))
	conRem.commit()
	nextHour = math.ceil(time.time()/3600)*3600
	schedEvents[message.author.id] = s.enterabs(nextHour, 10, schedule_coro(loop, checkReminder, message.author.id, message.guild.id, nextHour))
	await message.reply("You're set up to receive random (roughly weekly) automated reminders! ("+str(nextHour)+")")

async def unsubscribeReminders(message):
	curRem.execute("SELECT Last_Reminded FROM subscriptions WHERE User_ID = ? AND Server_ID = ?", (message.author.id, message.guild.id))
	existingSubs = curRem.fetchall()
	if len(existingSubs) == 0:
		await message.reply("You're not subscribed to reminder notifications!")
		return
	curRem.execute("DELETE FROM subscriptions WHERE User_ID = ? AND Server_ID = ?", (message.author.id, message.guild.id))
	conRem.commit()
	if message.author.id in schedEvents:
		s.cancel(schedEvents[message.author.id])
		del schedEvents[message.author.id]
	await message.reply("You've unsubscribed from reminder notifications.")

# Analysis functions
def word_freq_analysis(message):
	commandparts = message.content.split()
	if(len(commandparts) < 2):
		commandparts.append("server")
	
	for (path, dn, files) in os.walk('messages/'):
		for f in files:
			print(f)
			pd.read_csv(f'messages/{f}')
	messages = pd.concat([(pd.read_csv(f'messages/{f}'),print(f)) for (path, dn, files) in os.walk('messages/') for f in files])
	messages = messages.replace(np.nan, '')
	messages = messages[[(len(x) > 0 and x[0] != "$") for x in messages['content']]]
	messages = messages[~(messages['userid'] == 510251679283806209)]
	
	byline = "overall"
	
	if(commandparts[1] == "server"):
		server = message.guild.id
		if(len(commandparts) > 2):
			server = int(commandparts[2])
			byline = "in that server"
		else:
			byline = "in this server"
		messages = messages[messages['serverid'] == server]
	elif(commandparts[1] == "channel"):
		channel = message.channel.id
		if(len(commandparts) > 2):
			channel = commandparts[2]
			if(channel[0] == "<"):	
				channel = channel[2:-1] # Strip off extra characters in mentions
			byline = "in that channel"
		else:
			byline = "in this channel"
		messages = messages[messages['channelid'] == channel]
	elif(commandparts[1] == "user"):
		server = message.guild.id
		messages = messages[messages['serverid'] == server]
		user = message.author.id
		if(len(commandparts) > 2):
			user = commandparts[2]
			if(user[0] == "<"):	
				user = user[2:-1] # Strip off extra characters in mentions
			byline = "by that user"
		else:
			byline = "by you"
		messages = messages[messages['userid'] == user]
	elif(re.search("<[@#]\\d+>", commandparts[1])):
		if(commandparts[1][1] == "@"):
			server = message.guild.id
			messages = messages[messages['serverid'] == server]
			user = commandparts[1][2:-1]
			byline = "by that user"
			messages = messages[messages['userid'] == user]
		else:
			channel = commandparts[1][2:-1]
			byline = "in that channel"
			messages = messages[messages['channelid'] == channel]
	else:
		byline = 'overall, ignoring "'+commandparts[1]+'"'
		
	text = messages['content']
	print(text)
	text = [re.sub("https?://[^\\x00-\\x20]+\\.[^\\x00-\\x20]+", "", x) for x in text] # Remove URLs
	text = [re.sub("<:.+?:\\d+>", "", x) for x in text] # Remove custom emojis
	text = [re.sub("<[@#]\\d+>", "", x) for x in text] # Remove mentions
	#text = [re.sub("'", "", x) for x in text] # Remove 's to simplify words (don't -> dont)
	text = [re.sub("[^A-Za-z' ]", "", x) for x in text] # Alpha only
	text = [x.lower() for x in text] # Lowercase
	text = [x.split() for x in text] # Split on spaces
	words = [word for msg in text for word in msg] # Flatten, remove blanks
	unique_words = set(words)
	word_freqs = [sum([x == w for x in words])/len(words) for w in unique_words]
	discordMonograms = pd.DataFrame(list(zip(unique_words, word_freqs)), columns = ['word', 'freqDisc'])
	
	monograms = pd.read_table('analysis/count_1w.csv', names=["word", "freq"])
	monograms.freq = monograms.freq/1024908267229 # ~ 1 trillion total words in database
	
	mergeWords = discordMonograms.merge(monograms, on='word', how='outer')
	mergeWords.freq = mergeWords.freq.fillna(1e-8)
	mergeWords.freqDisc = mergeWords.freqDisc.fillna(1/(2*len(words)))
	mergeWords['diff'] = mergeWords.freqDisc - mergeWords.freq
	mergeWords = mergeWords.sort_values(by="diff", ascending=False)
	
	wordUse = mergeWords.word.tolist()
	wordUse = [x for x in wordUse if x not in stopwds]
	
	return (byline,wordUse[0:5])
	
def parseConversations(snowflakeFrom):
	messages = pd.concat([pd.read_csv(f'messages/{file[0]}') for (path, dn, file) in os.walk('messages/')])

@client.event
async def on_ready():
	loop = asyncio.get_running_loop()
	curRem.execute("SELECT * FROM subscriptions")
	subs = curRem.fetchall()
	next_hour = math.ceil(time.time()/3600)*3600
	for user_id, guild_id, *_ in subs:
		schedEvents[user_id] = s.enterabs(next_hour, 10, schedule_coro(loop, checkReminder, user_id, guild_id, next_hour))
	threading.Thread(target=scheduler_loop, daemon=True).start()
	print(f'Responder logged in as {client.user}')

@client.event
async def on_message(message):
	if(message.author.bot):
		return
	if(message.content.startswith("$")):
		if(message.content.startswith("$help")):
			await message.channel.send(helptext)
		elif(message.content.startswith("$topwords")):
			byline, topWords = word_freq_analysis(message)
			await message.channel.send(f"Top words that I've seen {byline}: \n1. {topWords[0]}\n2. {topWords[1]}\n3. {topWords[2]}\n4. {topWords[3]}\n5. {topWords[4]}")
		elif(message.content.startswith("$fullrefresh")):
			if(message.author.id == 234819459884253185):
				print("Ignoring refresh command for monitor")
			else:
				await message.channel.send("Hey! You're not allowed to touch that button!")
		elif(message.content.startswith("$remindme")):
			await sendReminder(message.author, message.channel, message.created_at)
		elif(message.content.startswith("$remindstats")):
			await sendRemindStats(message.author, message.channel)
		elif(message.content.startswith("$setreminder")):
			await setReminder(message)
		elif(message.content.startswith("$subreminders")):
			await subscribeReminders(message)
		elif(message.content.startswith("$unsubreminders")):
			await unsubscribeReminders(message)
		elif(len(message.content) > 1 and message.content[1].isnumeric()):
			print("Ignoring likely money amount or LaTeX")
		elif(len(message.content) > 1 and message.content[1] == "\\"):
			print("Ignoring likely LaTeX")
		else:
			command = message.content.split()[0][1:]
			await message.channel.send(f"I don't know how to '{command}'. Maybe complain to <@234819459884253185>.")
	# Check for reminders
	if (re.search(r"\bremind +me\b", message.content, re.I) or
		(re.search(r"\bsometime\b", message.content, re.I) and re.search(r"\bi('?ll)?\b", message.content, re.I)) or
		re.search(r"\bnotes? +to\b.*\b(self|me)\b", message.content, re.I)):
		curRem.execute("INSERT INTO reminders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (message.id, message.author.name, message.author.id, message.channel.id, message.guild.id, message.created_at, 0, 0, "New"))
		conRem.commit()

@client.event
async def on_reaction_add(reaction, user):
	if reaction.message.id in remBot and user.id != client.user.id:
		origFlake = remOrig[remBot.index(reaction.message.id)]
		curRem.execute("SELECT Author_ID from reminders WHERE Snowflake = ?", (origFlake,))
		intendedUser = curRem.fetchone()[0]
		if user.id == intendedUser:
			if reaction.emoji == "✅":
				curRem.execute("UPDATE reminders SET Status = 'Done' WHERE Snowflake = ?", (origFlake,))
				conRem.commit()
			elif reaction.emoji == "❎":
				curRem.execute("UPDATE reminders SET Status = 'Invalid' WHERE Snowflake = ?", (origFlake,))
				conRem.commit()
			elif reaction.emoji == "💤":
				curRem.execute("UPDATE reminders SET Snooze = 10 WHERE Snowflake = ?", (origFlake,))
				conRem.commit()
			elif reaction.emoji == "⏭":
				await sendReminder(user, reaction.message.channel, int(time.time()))
			else:
				print("Emoji "+str(reaction.emoji)+" not recognized")
		else:
			print("Wrong user reacted!")

if not os.path.isfile('analysis/count_1w.csv'):
	urllib.request.urlretrieve('https://norvig.com/ngrams/count_1w.txt', 'analysis/count_1w.csv')

def scheduler_loop():
	while True:
		s.run(blocking=False)
		time.sleep(0.5)

client.run(open('secret.txt', 'r').readline())
