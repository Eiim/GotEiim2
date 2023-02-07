import discord
import csv

# Pycord stuff begins here

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

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
		else:
			command = message.content.split()[0][1:]
			await message.channel.send(f"I don't know how to '{command}'. Maybe complain to <@234819459884253185>.")
	
client.run(open('secret.txt', 'r').readline())