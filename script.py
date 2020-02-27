import xml.etree.ElementTree as et
import os
import sys
import re

def findIndices(pattern, text):
    reList = []
    for match in re.finditer(pattern, text):
        reList.append(match.start())
    return reList

def formatHandler(cell):
    #handling linebreaks
    cell = re.sub("<br/>", "\n", cell)
    #handling teletype
    cell = re.sub("</?tt>", "*", cell)
    #handling bold
    cell = re.sub("</?b>", "**", cell)
    #handling italics
    cell = re.sub("</?em>", "*", cell)
    #handling links
    cell = re.sub('<a href="', "", cell)
    cell = re.sub('" class="(.*)</a>', "", cell)

    #handling lists
    ul = findIndices("</?ul>", cell)
    ol = findIndices("</?ol>", cell)
    tempList = cell
    if len(ul)>1:
        tempList = cell[ul[0]:ul[1]+5]
        tempList = re.sub("[ \t\n]*</?ul>[ \t\n]*", "", tempList)
        tempList = re.sub("[ \t\n]*<li>[ \t\n]*", "* ", tempList)
        tempList = re.sub("[ \t\n]*</li>[ \t\n]*", "\n", tempList)
    if len(ol)>1:
        tempList = cell[ol[0]:ol[1]+5]
        tempList = re.sub("[ \t\n]*</?ol>[ \t\n]*", "", tempList)
        tempList = re.sub("[ \t\n]*<li>[ \t\n]*", "1. ", tempList)
        tempList = re.sub("[ \t\n]*</li>[ \t\n]*", "\n", tempList)


    return tempList

def tableParser(allText):
    stepDescription = []
    expectedResult = []
    allText = str(allText)
    tbodyTagList = findIndices("<tbody>", allText)
    tableNum = 0
    if len(tbodyTagList)>1:
        tableNum = int(input("There are "+str(len(tbodyTagList))+" tables in the comment, please type which table you'd like (e.g. 1): ")) -1
    endTbodyTagList = findIndices("</tbody", allText)
    tableText = allText[tbodyTagList[tableNum]+7: endTbodyTagList[tableNum]]#+7 because that's the length of the <tbody> tag
    rowTagList = findIndices("<tr>", tableText)
    endRowTagList = findIndices("</tr>", tableText)
    for i in range(1,len(endRowTagList)):
        if rowTagList[i]+5 == endRowTagList[i]:
            continue
        else:
            rowText = tableText[rowTagList[i]+4:endRowTagList[i]]
            cellList = findIndices("<td class='confluenceTd'>", rowText)
            endCellList = findIndices("</td>", rowText)
            tempStepDescription = formatHandler(rowText[cellList[0]+25:endCellList[0]])
            tempExpectedResult = formatHandler(rowText[cellList[1]+25:endCellList[1]])
            stepDescription.append(tempStepDescription)
            expectedResult.append(tempExpectedResult)
    return stepDescription, expectedResult

#Reading
#user inputs name of file
filename = str(input("Name of the file to convert (don't include extension): "))
#parse an xml file by name (has to be in same directory) as tree
tree = et.parse("%s.xml"%filename)
#root of the xml tree of ticket
troot = tree.getroot()
#tCase = Actual ticket with needed fields as children
tCase = troot.find('channel').find('item')
title = ""
references = ""
priority = ""
milestone = ""

#Jira Fix versions -> testrail milestone
try:
    milestone = tCase.find('fixVersion').text
except:
    print("Can't find fixversion")
#Jira summary -> testrail title
try:
    title = tCase.find('summary').text
except:
    print("Can't find summary")
#Jira issue key -> testrail references
try:
    references = tCase.find('key').text
except:
    print("Can't find key")
#Jira Priority -> testrail priority
try:
    priority = tCase.find('priority').text
except:
    print("Can't find priority")

#mapping jira priorities to testrail priorities
if priority=="Major":
    priority = "High"
elif priority=="Minor":
    priority = "Medium"
elif priority == "Trivial":
    priority = "Low"

#comments - contains the comment including the test cases
comments = tCase.find('comments')
#testCommentInd = the array num of comment containing test cases
testCommentInd = 0
#picks the comment with most data inside
for i in range(1,len(comments)):
    if len(comments[testCommentInd].text)<len(comments[i].text):
        testCommentInd = i
tempTestComment = comments[testCommentInd]
#deleting all other comments (without this a duplicate error is called repeatedly - don't know why but suspect it has something to do with xml comments formatting in jira)
for i in range(len(comments)-1,-1,-1):
    if comments[i].attrib!=tempTestComment.attrib:
        comments.remove(comments[i])
#testComment = comment text containing table with test cases
testComment = tempTestComment.text
#Since we're using xml parsing for html parsing - we need a root for the parser
#adding <root> and </root>
prefix = "<root>\n"
suffix = "\n</root>"
testComment = prefix + testComment + suffix

#HTML(tbh it's really XML) parsing time T.T
stepDescription, expectedResult = tableParser(testComment)

#read testrailTemplate.xml
templateTree = et.parse("testrailTemplate.xml")
templateRoot = templateTree.getroot()
templateCase = templateRoot.find('sections').find('section').find('cases').find('case')

#adding Jira information to template (on python and not the template)
templateCase.find('title').text = title
templateCase.find('references').text = references
templateCase.find('priority').text = priority
templateCase.find('milestone').text = milestone
#adding Test cases and calculating time estimate (base 2m + n steps * 2m step time)
timeEstimate = 2
templateSteps = templateCase.find('custom').find('steps_separated')
for i in range(len(stepDescription)):
    step = et.SubElement(templateSteps, 'step')
    caseIndex = et.SubElement(step, 'index')
    caseIndex.text = str(i+1)
    caseContent = et.SubElement(step, 'content')
    caseContent.text = stepDescription[i]
    caseExpected = et.SubElement(step, 'expected')
    caseExpected.text = expectedResult[i]
    timeEstimate+=3
#converting timeEstimate from minutes to seconds
timeEstimate*=60
#adding calculated time estimate to template
templateCase.find('estimate').text = str(timeEstimate)


#Writing tree to file
templateTree.write('%sTestrail.xml'%filename)
#opening file and saving to string tRFile
with open('%sTestrail.xml'%filename, 'r') as file:
    tRFile = file.read()
#deleting file
os.remove("%sTestrail.xml"%filename)
#removing root tags (<suite> and </suite>)
tRFile = tRFile[8:-9]
#writing string back to file
with open('%sTestrail.xml'%filename, 'w') as file:
    file.write(tRFile)
#created by Chun Kei (Argus) Li
