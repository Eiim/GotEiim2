import datetime
import sqlite3
import sqlite_zstd
import nltk
import re

# Connect to message database
conMsg = sqlite3.connect("goteiim.db")
conMsg.enable_load_extension(True)
sqlite_zstd.load(conMsg)
curMsg = conMsg.cursor()

# Set datetime adapter/covnerter (converter may not be necessary)
def adapt_datetime_epoch(val):
    """Adapt datetime.datetime to Unix timestamp."""
    return int(val.timestamp())
sqlite3.register_adapter(datetime.datetime, adapt_datetime_epoch)

def convert_timestamp(val):
    """Convert Unix epoch timestamp to datetime.datetime object."""
    return datetime.datetime.fromtimestamp(int(val))
sqlite3.register_converter("timestamp", convert_timestamp)

# Connect to reminder database
conRem = sqlite3.connect("reminders.db")
curRem = conRem.cursor()
curRem.execute("""DROP TABLE IF EXISTS reminders""")
curRem.execute("""CREATE TABLE IF NOT EXISTS reminders (
				Snowflake INTEGER,
				Author_Name TEXT,
				Author_ID INTEGER,
				Channel_ID INTEGER,
				Server_ID INTEGER,
				Created INTEGER,
				Last_Reminded INTEGER,
				Snooze INTEGER,
				Status TEXT
				)""")
conRem.commit()

print("Connected to databases")

snowball = []
for row in curMsg.execute("SELECT Contents, Snowflake FROM messages"):
	if (re.search(r"\bremind +me\b", row[0], re.I) or
		(re.search(r"\bsometime\b", row[0], re.I) and re.search(r"\bi('?ll)?\b", row[0], re.I)) or
		re.search(r"\bnotes? +to\b.*\b(self|me)\b", row[0], re.I)):
		snowball.append(row[1])

print("Retrieved snowball ("+str(len(snowball))+" values)")

for snow in snowball:
	curMsg.execute("SELECT Snowflake, Author_Name, Author_ID, Channel_ID, Server_ID, Created FROM messages WHERE Snowflake = ?", (snow,))
	curRem.execute("INSERT INTO reminders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", curMsg.fetchone() + (0, 0, "New"))
conRem.commit()

print("Done!")