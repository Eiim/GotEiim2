import discord
import pandas as pd
import numpy as np
import urllib.request
import re
import os
import nltk

# Pycord stuff begins here
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

# Stopwords from Snowball
stopwds = ["i","me","my","myself","we","our","ours","ourselves","you","your","yours","yourself","yourselves","he","him","his","himself","she","her","hers","herself","it","its","itself","they","them","their","theirs","themselves","what","which","who","whom","this","that","these","those","am","is","are","was","were","be","been","being","have","has","had","having","do","does","did","doing","would","should","could","ought","i'm","you're","he's","she's","it's","we're","they're","i've","you've","we've","they've","i'd","you'd","he'd","she'd","we'd","they'd","i'll","you'll","he'll","she'll","we'll","they'll","isn't","aren't","wasn't","weren't","hasn't","haven't","hadn't","doesn't","don't","didn't","won't","wouldn't","shan't","shouldn't","can't","cannot","couldn't","mustn't","let's","that's","who's","what's","here's","there's","when's","where's","why's","how's","a","an","the","and","but","if","or","because","as","until","while","of","at","by","for","with","about","against","between","into","through","during","before","after","above","below","to","from","up","down","in","out","on","off","over","under","again","further","then","once","here","there","when","where","why","how","all","any","both","each","few","more","most","other","some","such","no","nor","not","only","own","same","so","than","too","very","will"]

helptext = """GotEiim2 Help:
`$help`: Get help for GotEiim2
  - format: `$help`
`$topwords`: Get the most-used words compared to their overall usage in English, filtered by a server, channel, or user.
  - format: `$topwords [category] [specifier]` or `$topwords [specifier]`
    - `category`: One of "server", "channel", or "user". Optional, defaults to "server".
    - `specifier`: A snowflake ID or mention of the server, channel, or user to filter on. Optional, defaults to the server/channel the message is sent in or the user who sent it. If `category` is excluded, this must be a user or channel mention.
"""

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
		elif(len(message.content) > 1 and message.content[1].isnumeric()):
			print("Ignoring likely money amount or LaTeX")
		elif(len(message.content) > 1 and message.content[1] == "\\"):
			print("Ignoring likely LaTeX")
		else:
			command = message.content.split()[0][1:]
			await message.channel.send(f"I don't know how to '{command}'. Maybe complain to <@234819459884253185>.")
	
if not os.path.isfile('analysis/count_1w.csv'):
	urllib.request.urlretrieve('https://norvig.com/ngrams/count_1w.txt', 'analysis/count_1w.csv')

client.run(open('secret.txt', 'r').readline())
