
print("About to install the library")

install.packages("academictorrents")



print("About to import the library")

require(academictorrents)




print("About to start a download")

filename = at.get("323a0048d87ca79b68f12a6350a57776b6a3b7fb")
