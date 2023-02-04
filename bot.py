import discord
import os

# File managing stuff here
def writeLine(category, snowflake, data):
	if(not os.path.exists('./'+category)):
		os.mkdir('./'+category)
	snowflakePrefix = round(snowflake/1e15)
	fileName = f'./{category}/{int(snowflakePrefix)}.csv'
	if(not os.path.isfile(fileName)):
		f = open(fileName, 'a')
		f.write('snowflake,user,created,clean_content,attachments\n')
	else:
		f = open(fileName, 'a')
	f.write(data+'\n')
	f.close()

# Pycord stuff begins here

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
	print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
	attachments = ' '.join([str(a) for a in message.attachments])
	writeLine("messages", message.id, f'{message.id},{message.author.name}#{message.author.discriminator},{message.created_at},{message.clean_content},{attachments}')

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

@client.event
async def on_message_edit(before, after):
	print(after.content)

client.run(open('secret.txt', 'r').readline())

#<CustomActivity name='testtest' emoji=<PartialEmoji animated=False name='🙏' id=None>>
#<Activity type=<ActivityType.playing: 0> name='Super Hexagon' url=None details=None application_id=443161212969156608 session_id=None emoji=None>
#<Activity type=<ActivityType.listening: 2> name='Impromptu Live Adam Q&A!!' url=None details=None application_id=834488117758001152 session_id=None emoji=None>