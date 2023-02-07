library(tidyverse)
library(stopwords)

# Download word frequency databases if missing
if(length(which(list.files() == 'count_1w.csv')) == 0) {
  download.file('https://norvig.com/ngrams/count_1w.txt', 'count_1w.csv')
}
if(length(which(list.files() == 'count_2w.csv')) == 0) {
  download.file('https://norvig.com/ngrams/count_2w.txt', 'count_2w.csv')
}

# Load databases into memory
monograms <- read_tsv('count_1w.csv', col_names=c("word", "count"), col_types="cd")
monograms <- monograms %>%
  mutate(freq = count/1024908267229) %>%
  select(-count)

digrams <- read_tsv('count_2w.csv', col_names=c("word", "count"), col_types="cd")
digrams <- digrams %>%
  mutate(freq = count/1e12) %>% # What's the actual digram count?
  select(-count)

# Load Discord message data
messages <- data.frame(snowflake=double(0), user=character(0), channel=character(0), channelid=double(0), server=character(0), serverid=double(0), created=double(0), cleancontent=character(0), attachments=character(0))
for(dat in list.files("../messages")) {
  messages <- rbind(messages, read_csv(paste0("../messages/", dat), col_types="dccdcdTcc"))
}

text = messages$clean_content
text = gsub("https?://[^\\x00-\\x20]+\\.[^\\x00-\\x20]+", "", text, perl=TRUE) # Remove (obvious) URLs
text = gsub("'", "", text) # Remove 's
text = gsub("[^A-Za-z ]", " ", text) # Alpha only
text = tolower(text) # Lowercase
text = strsplit(text, " ") # Split by spaces
text = lapply(text, function(x){x[x != ""]}) # Remove blanks

words = unlist(text)
uniqueWords = unique(words)
wordFreqs = unlist(lapply(uniqueWords, function(x){sum(words == x)/length(words)}))
discordMonograms <- data.frame(word = uniqueWords, freqDisc = wordFreqs)

mergeWords <- full_join(monograms, discordMonograms, by="word") %>%
  replace_na(list(freq = 1e-8, freqDisc = 1/(2*length(words)))) %>%
  mutate(diff=freqDisc-freq)

stpwds <- stopwords(language="en", source="snowball")

wordUse <- mergeWords$word[order(-mergeWords$diff)]
wordUse <- wordUse[!wordUse %in% stpwds]
topWords <- head(wordUse, n=5)
bottomWords <- tail(wordUse, n=5)

print(topWords)
print(bottomWords)
