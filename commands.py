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

# Analysis functions
def word_freq_analysis(message):
	messages = pd.concat([pd.read_csv(f'messages/{file[0]}') for (path, dn, file) in os.walk('messages/')])
	messages = messages.replace(np.nan, '')
	messages = messages[[(len(x) == 0 or x[0] != "$") for x in messages['clean_content']]]
	messages = messages[~(messages['user'] == 'GotEiim#7055')]
	
	text = messages['clean_content']
	text = [re.sub("https?://[^\\x00-\\x20]+\\.[^\\x00-\\x20]+", "", x) for x in text] # Remove URLs
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
	
	return wordUse[0:5]
	
def parseConversations(snowflakeFrom):
	messages = pd.concat([pd.read_csv(f'messages/{file[0]}') for (path, dn, file) in os.walk('messages/')])

@client.event
async def on_ready():
	print(f'Commander logged in as {client.user}')

@client.event
async def on_message(message):
	if(message.author.bot):
		return
	if(message.content.startswith("$")):
		if(message.content.startswith("$help")):
			await message.channel.send("Listen, I don't do much right now. I just spy on you, like Google. 👁️")
		elif(message.content.startswith("$topwords")):
			topWords = word_freq_analysis(message)
			await message.channel.send(f"Top words that I've seen overall: \n1. {topWords[0]}\n2. {topWords[1]}\n3. {topWords[2]}\n4. {topWords[3]}\n5. {topWords[4]}")
		else:
			command = message.content.split()[0][1:]
			await message.channel.send(f"I don't know how to '{command}'. Maybe complain to <@234819459884253185>.")
	
if not os.path.isfile('analysis/count_1w.csv'):
	urllib.request.urlretrieve('https://norvig.com/ngrams/count_1w.txt', 'analysis/count_1w.csv')
nltk.download('stopwords')

client.run(open('secret.txt', 'r').readline())