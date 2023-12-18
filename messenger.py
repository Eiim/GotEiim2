import discord
from os import listdir, remove
from os.path import isfile, join
import csv
import time

# Pycord stuff begins here
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
	print(f'Messenger logged in as {client.user}')
	
	channel = # Add channel/thread ID here
	folder = "../mosers_powers/messages/"
	
	while True:
		files = [join(folder, f) for f in listdir(folder) if isfile(join(folder, f))]
		for file in files:
			text = open(file, 'r').readline()
			ch = await client.fetch_channel(channel)
			await ch.send(text)
			remove(file)
			print(f'Sent message in file {file}')
		time.sleep(60)

client.run(open('secret.txt', 'r').readline())