import datetime
import discord
import os
import csv
import sqlite3

# Connect to database
con = sqlite3.connect("goteiim.db")
cur = con.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS messages (
				Snowflake INTEGER PRIMARY KEY,
				Author_Name TEXT,
				Author_ID INTEGER,
				Channel_Name TEXT,
				Channel_ID INTEGER,
				Server_Name TEXT,
				Server_ID INTEGER,
				Created INTEGER,
				Contents TEXT,
				Attachments TEXT,
				Reply_TO INTEGER
			)""")
con.commit()

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
	cur.execute("INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
				(message.id, message.author.name, message.author.id, message.channel.name, message.channel.id, message.guild.name, message.guild.id, message.created_at, message.content, attachments, reference))
	con.commit()

@client.event
async def on_message_delete(message):
	print(message.id)
	print(type(message.id))
	cur.execute("DELETE FROM messages WHERE Snowflake = ?", (message.id,))
	con.commit()

@client.event
async def on_message_edit(before, after):
	attachments = ' '.join([str(a) for a in after.attachments])
	reference = ''
	if(after.reference):
		reference = after.reference.message_id
	cur.execute("""UPDATE messages SET
					Author_Name = ?,
					Author_ID = ?,
					Channel_Name = ?,
					Channel_ID = ?,
					Server_Name = ?,
					Server_ID = ?,
					Created = ?,
					Contents = ?,
					Attachments = ?,
					Reply_TO = ?
					WHERE Snowflake = ?
				""", (after.author.name, after.author.id, after.channel.name, after.channel.id, after.guild.name, after.guild.id, after.created_at, after.content, attachments, reference, after.id))
	con.commit()

@client.event
async def on_presence_update(before, after):
	#return # temporarily disable
	if(after.guild.id != 481120236318228480): # Raisels-exclusive :triumph:
		return
	
	if(before.status != after.status):
		print(f'status change: {after.nick} ({after.name}) from {before.status} to {after.status}')
	else:
		print(f'activity change: {after.nick} ({after.name}) from {before.activity} to {after.activity}')
		print([a.to_dict() for a in after.activities])

client.run(open('secret.txt', 'r').readline())

#<CustomActivity name='testtest' emoji=<PartialEmoji animated=False name='🙏' id=None>>
#<Activity type=<ActivityType.playing: 0> name='Super Hexagon' url=None details=None application_id=443161212969156608 session_id=None emoji=None>
#<Activity type=<ActivityType.listening: 2> name='Impromptu Live Adam Q&A!!' url=None details=None application_id=834488117758001152 session_id=None emoji=None>