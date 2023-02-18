import discord
import os
import csv

# File managing stuff here
def writeLine(category, snowflake, data):
	if(not os.path.exists('./'+category)):
		os.mkdir('./'+category)
	snowflakePrefix = int(snowflake/1e15)
	fileName = f'./{category}/{int(snowflakePrefix)}.csv'
	if(not os.path.isfile(fileName)):
		f = open(fileName, 'a')
		w = csv.writer(f)
		w.writerow(['snowflake','user','userid','channel','channelid','server','serverid','created','content','attachments','replyto'])
	else:
		f = open(fileName, 'a')
		w = csv.writer(f)
	w.writerow(data)
	f.close()

def removeLine(category, snowflake):
	snowflakePrefix = int(snowflake/1e15)
	fileName = f'./{category}/{int(snowflakePrefix)}.csv'
	if(not os.path.isfile(fileName)):
		return
	f = open(fileName, 'r')
	lines = f.readlines()
	f = open(fileName, 'w')
	for line in lines:
		if(not line.startswith(str(snowflake))):
			f.write(line)

def editLine(category, snowflake, data):
	print(snowflake)
	snowflakePrefix = int(snowflake/1e15)
	fileName = f'./{category}/{int(snowflakePrefix)}.csv'
	if(not os.path.isfile(fileName)):
		return
	f = open(fileName, 'r')
	lines = f.readlines()
	f = open(fileName, 'w')
	w = csv.writer(f)
	for line in lines:
		if(line.startswith(str(snowflake))):
			w.writerow(data)
		else:
			f.write(line)

# Pycord stuff begins here

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
	print(f'Monitor logged in as {client.user}')

@client.event
async def on_message(message):
	attachments = ' '.join([str(a) for a in message.attachments])
	reference = ''
	if(message.reference):
		reference = message.reference.message_id
	writeLine("messages", message.id, [message.id, message.author.name, message.author.id, message.channel.name, message.channel.id, message.guild.name, message.guild.id, message.created_at, message.content, attachments, reference])

@client.event
async def on_message_delete(message):
	removeLine("messages", message.id)

@client.event
async def on_message_edit(before, after):
	print(after.id)
	attachments = ' '.join([str(a) for a in after.attachments])
	reference = ''
	if(after.reference):
		reference = after.reference.message_id
	editLine("messages", after.id, [after.id, after.author.name, after.author.id, after.channel.name, after.channel.id, after.guild.name, after.guild.id, after.created_at, after.content, attachments, reference])

@client.event
async def on_presence_update(before, after):
	return # temporarily disable
	if(after.guild.id != 481120236318228480): # Raisels-exclusive :triumph:
		return
	
	if(before.status != after.status):
		print(f'status change: {after.nick} ({after.name}#{after.discriminator}) from {before.status} to {after.status}')
	else:
		print(f'activity change: {after.nick} ({after.name}#{after.discriminator}) from {before.activity} to {after.activity}')
		print([a.to_dict() for a in after.activities])

client.run(open('secret.txt', 'r').readline())

#<CustomActivity name='testtest' emoji=<PartialEmoji animated=False name='🙏' id=None>>
#<Activity type=<ActivityType.playing: 0> name='Super Hexagon' url=None details=None application_id=443161212969156608 session_id=None emoji=None>
#<Activity type=<ActivityType.listening: 2> name='Impromptu Live Adam Q&A!!' url=None details=None application_id=834488117758001152 session_id=None emoji=None>