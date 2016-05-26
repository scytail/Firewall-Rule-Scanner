#!/bin/env python2.7
#
# ReportGenerator.py
# 
# A script written to traverse a file system and pull relevant data about IPs and data connections for users
# 
# Author:   Ben Schwabe
# Created:  2015.09.09

import os
import sys
import datetime
import gzip
import subprocess
import platform

#Change to what directory you want the system to start looking for conn.log
#it is recommended that you narrow down the path as small as possible, since the code has to scan every file in every subdirectory in the root directory
rootDirectory = "/full/path/to/folder/containing/folders/with/dated/logs"

#important columns (starting at 0)
source_ip = 2
source_port = 3
destination_ip = 4
destination_port = 5
protocol = 6
success = 11

defaultCols = [source_ip,destination_ip,destination_port,protocol] #used for setting the default recorded columns
success_data = "SF"

#command data defaults
importantCols = [0,0,1,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0] #used for recording columns
ipSearchList = []
lastDateToSearch = "-1" #optional variable to confine the search to after a current day, in the format yyyymmdd

#A class to store individual lines of data in memory for later use (to free up the CPU for processing other lines)
class DataContainer:
    #defines the class and initializes all variables
    #self: implicit parameter containing information on the instance of the class
    #lineArray: an array of data to store in memory for later use
    def __init__(self,dataArray):
        self.dataArray = dataArray

#searches for a number in a sorted list (using a binary search), and if it isn't there, inserts it in the proper location
#targetList is the list to run through (must be sorted least to greatest)
#targetColumn is the index of the sub-list that targetList holds that will compare to item
#item is the list to compare and insert into the targetList if it is unique (compares the data at the index of targetColumn and destination_port)
def binaryInsert(targetList,targetColumn,item):
    first = 0
    last = len(targetList)-1
    found = False
    if targetList != []: #list is not empty
        while first<=last and not found: #loops through the list using a basic divide and conquer algorithm
            midpoint = (first + last)//2
            if targetList[midpoint].dataArray[targetColumn] == item[targetColumn] and targetList[midpoint].dataArray[destination_port] == item[destination_port]:
                found = True #end the loop because the entry is already in the list
            else:
                if item[targetColumn] < targetList[midpoint].dataArray[targetColumn]:
                    last = midpoint-1
                else:
                    first = midpoint+1
                    
        if not found:
            if targetList[midpoint].dataArray[targetColumn] < item[targetColumn]:  #place after the last checked item
                targetList.insert(midpoint+1,DataContainer(item))
            else:
                targetList.insert(midpoint,DataContainer(item)) #place before the last checked item
    else:
        targetList.append(DataContainer(item))
    return targetList

#Runs through the list of command line arguments
i=1
while i < len(sys.argv):
    if sys.argv[i] == "-i":
        i += 1
        while i < len(sys.argv): #scans the next arguments in the list for data until the next command or end of command list
            if sys.argv[i][0] != "-":
                inputFile = open(sys.argv[i],"r")
                for line in inputFile:
                    ipSearchList.append(line[:len(line)-1]) #append the ip from the file (subtracting off the '\n' from the end) to the list of ips to look for
                i += 1
            else:
                break
                
    elif sys.argv[i] == "-l":
        i += 1
        while i < len(sys.argv): #scans the next arguments in the list for data until the next command or end of command list
            if sys.argv[i][0] != "-":
                ipSearchList.append(sys.argv[i]) #append the ip to the list (subtracting off the '\n' from the end)
                i += 1
            else:
                break
                
    elif sys.argv[i] == "-c":
        i+=1
        importantCols = [0]*24
        while i < len(sys.argv): #scans the next arguments in the list for data until the next command or end of command list
            if sys.argv[i][0] != "-":
                if sys.argv[i].lower() == "all": #special command to append all columns to the file
                    for element in range(0,len(importantCols)):
                        importantCols[element] = 1
                elif sys.argv[i].lower() == "default": #special command to append only the program defaults to the file
                    for element in defaultCols:
                        importantCols[element] = 1
                else:
                    importantCols[int(sys.argv[i])] = 1
                i += 1
            else:
                break
    
    elif sys.argv[i] == "-d":
        i+=1
        lastDateToSearch = sys.argv[i]
        i+=1
                
    elif sys.argv[i] == "-h" or sys.argv[i] == "-?" or sys.argv[i] == "-help":
        print "PythonGenerator.py\n"
        print "USAGE                        Description"
        print "-i <list of input files>     A list of files that contain IPs to search for"
        print "-l <IP list>                 A command line list of IPs to search for"
        print "-c <numeric list of columns> A numeric list of columns from the files to log. Use 'default' to save the default columns and 'all' to save all the columns"
        print "-d <date in format yyyymmdd> A valid date in the format yyyymmdd, where the date is the oldest date to search for (inclusively). If this is not included, it will scan all dates."
        print "-h                           displays this dialog"
        print "\n Please see the included 'README' file for more detailed information."
        i+=1
    else:
        raise KeyError("'" + sys.argv[i] + "' is not a valid argument. Use -h for a list of commands.")

#build the data structure that will hold the IPs to output to a file
resultList = []
for ip in ipSearchList:
    #built so that for each element in resultList (i.e. for each IP being searched), there is a dictionary of lists, each list containing the line data where that specific ip was found
    resultList.append({"source":[],"destination":[]})

filesRead = 0

print "Currently traversing the file system for your query. This may take a while...\n"

#run the unix 'find' command, or windows alternative (since it is faster than natively executing python's 'os.walk()' method), and output the result to a variable as a string
if platform.system() == "Windows":
    #findCmdOutputString = subprocess.Popen(['dir','/s','/b',"{0}".format(''.join([rootDirectory,'/*/conn.*.log.gz']))],stdout=subprocess.PIPE).stdout.read()
    print "THIS PROGRAM DOES NOT CURRENTLY WORK ON WINDOWS."
    findCmdOutputString = ""
else:
    findCmdOutputString = subprocess.Popen(['find',rootDirectory,'-name','conn.*.log.gz'],stdout=subprocess.PIPE).stdout.read()

files = findCmdOutputString.split("\n")#make a list of the results
files = files[:len(files)-1]#shave off the empty final argument

#traverse the file system to read the matching files
for currentFile in files:
    dateDirectoryList = currentFile.replace("\\","/").split("/") #divide the subdirectory into an ordered list of the directories the file is located in
    dateDirectory = dateDirectoryList[len(dateDirectoryList)-2] #get the closest directory (assumes that the filesystem will have deepest subdirectory be the date of the file)
    if dateDirectory >= lastDateToSearch: #the file we found is equal to or after the oldest date to scan
        with gzip.open(currentFile) as logFile:
            filesRead+=1
            
            #status update for the user
            print "Opened file {0} for reading...".format(currentFile),
            numLines = 0
            for lineBytes in logFile: #processes each line in the conn.log
                numLines+=1 #count the number of lines in the file
                line = lineBytes.decode("utf-8") #decode the line into a string
                if not (line[0] == "#"): #eliminates the commented out lines (since these aren't necessarily in standard format and aren't important)
                    
                    lineArray = line.split("\t") #split the line into an array based on separation by single tabs between pieces of data and then picks out only the relevant data from each line
                    
                    if lineArray[success] == success_data: #only want connections that succeeded in connecting
                        
                        for ipIndex in range(0,len(ipSearchList)):
                            ip = ipSearchList[ipIndex]
                            
                            if ip == lineArray[source_ip]: #match found in the source IP
                                resultList[ipIndex]["source"] = binaryInsert(resultList[ipIndex]["source"],destination_ip,lineArray)
                                
                            elif ip == lineArray[destination_ip]: #match found in the destination IP
                                resultList[ipIndex]["destination"] = binaryInsert(resultList[ipIndex]["destination"],source_ip,lineArray)
        print "\nRead {0} lines.".format(numLines)

print "\nFile scan has been completed. Writing results to files."

filesCreated = 0

#create the report
for ipIndex in range(0,len(ipSearchList)):
    #only create a report file if there are things to log
    if resultList[ipIndex]["source"] != [] or resultList[ipIndex]["destination"] != []:
        report = open(str(ipSearchList[ipIndex]) + ".csv","w")
        filesCreated+=1
    
        #compile a list of matching source data to write (assuming there is some)
        if resultList[ipIndex]["source"] != []:
            for lineResult in resultList[ipIndex]["source"]:
                relevantData = []
                for i in range(0,len(importantCols)):
                    if importantCols[i] == 1:
                        relevantData.append(lineResult.dataArray[i])
                
                report.write(",".join(relevantData)) #writes a line to the report separating each element in the array with a comma
                
                if importantCols[23] != 1:
                    report.write("\n") #writes a newline to the file in case the last piece of data in a line isn't printed (this piece of data contains '\n' at the end of it)
        
        #compile a list of matching destination data to write (assuming there is some)
        if resultList[ipIndex]["destination"] != []:
            for lineResult in resultList[ipIndex]["destination"]:
                relevantData = []
                for i in range(0,len(importantCols)):
                    if importantCols[i] == 1:
                        relevantData.append(lineResult.dataArray[i])
                
                report.write(",".join(relevantData)) #writes a line to the report separating each element in the array with a comma
                
                if importantCols[23] != 1:
                    report.write("\n") #writes a newline to the file in case the last piece of data in a line from the logfile isn't printed (this piece of data contains '\n' at the end of it)
        
        report.close()
    
print "Read {0} files for your query. Data has been compiled into {1} files.".format(filesRead,filesCreated)
