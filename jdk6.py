#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Wu Liang
@contact: 
@date: 2014/06/23
"""

import os
import sqlite3
import urllib2
import shutil
import tarfile
import hashlib
import codecs

from mako.template import Template
from pyquery import PyQuery

currentPath = os.path.join(os.path.dirname(os.path.realpath(__file__)))
name = "JDK6"

baseName = "jdk6-zh"
output = baseName + ".docset"
appName = "dash-" + baseName
tarFileName = baseName + ".tgz"
feedName = baseName + ".xml"
version = "6"

urlPrefix = "http://tool.oschina.net/uploads/apidocs/jdk-zh/"
url = urlPrefix + "allclasses-frame.html"
content = urllib2.urlopen(url).read()
content = content.decode("utf-8").encode("utf-8")
jQuery = PyQuery(content)

items = jQuery(".FrameItemFont a").items()
results = []
for item in items:
    text = item.text()
    href = item.attr("href")
    results.append({
        "name": text,
        "type": "Class",
        "path": href
    })

# Step 1: create the docset folder
docsetPath = os.path.join(currentPath, output, "Contents", "Resources", "Documents")
if not os.path.exists(docsetPath):
    os.makedirs(docsetPath)

# Step 2: Copy the HTML Documentation
fin = codecs.open(os.path.join(docsetPath, "index.html"), "w", "utf-8")
newContent = jQuery.html()
fin.write(newContent)
fin.close()

# Step 2.1 创建每一个类的页面
for result in results:
    fields = result["path"].split("/")
    if len(fields) >= 2:
        dest = os.path.join(docsetPath, os.path.sep.join(fields[:-1]))
        if not os.path.exists(dest):
            os.makedirs(dest)
        fin = open(os.path.join(docsetPath, result["path"]), "w")
        fin.write(urllib2.urlopen(urlPrefix + result["path"]).read())
        fin.close()

# Step 2.2 下载CSS和JS
links = [
    urlPrefix + "stylesheet.css",
    urlPrefix + "/resources/inherit.gif"
]
for link in links:
    path = link.replace(url, "")
    fields = path.split("/")
    if len(fields) >= 2:
        dirPath = os.path.join(docsetPath, os.path.sep.join(fields[:-1]))
        if not os.path.exists(dirPath):
            os.makedirs(dirPath)
        fin = open(os.path.join(docsetPath, os.path.sep.join(fields)), "wb")
        fin.write(urllib2.urlopen(link).read())
        fin.close()

# Step 3: create the Info.plist file
infoTemplate = Template('''<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0">
<dict>
<key>CFBundleIdentifier</key>
<string>${name}</string>
<key>CFBundleName</key>
<string>${name}</string>
<key>DocSetPlatformFamily</key>
<string>${name}</string>
<key>dashIndexFilePath</key>
<string>index.html</string>
<key>dashIndexFilePath</key>
<string>index.html</string>
<key>isDashDocset</key><true/>
<key>isJavaScriptEnabled</key><true/>
</dict>
</plist>''')
infoPlistFile = os.path.join(currentPath, output, "Contents", "Info.plist")
fin = open(infoPlistFile, "w")
fin.write(infoTemplate.render(name = name))
fin.close()

# Step 4: Create the SQLite Index
dbFile = os.path.join(currentPath, output, "Contents", "Resources", "docSet.dsidx")
if os.path.exists(dbFile):
    os.remove(dbFile)
db = sqlite3.connect(dbFile)
cursor = db.cursor()

try:
    cursor.execute("DROP TABLE searchIndex;")
except Exception:
    pass

cursor.execute('CREATE TABLE searchIndex(id INTEGER PRIMARY KEY, name TEXT, type TEXT, path TEXT);')
cursor.execute('CREATE UNIQUE INDEX anchor ON searchIndex (name, type, path);')

insertTemplate = Template("INSERT OR IGNORE INTO searchIndex(name, type, path) VALUES ('${name}', '${type}', '${path}');")

# Step 5: Populate the SQLite Index
for result in results:
    sql = insertTemplate.render(name = result["name"], type = result["type"], path = result["path"])
    print sql
    cursor.execute(sql)
db.commit()
db.close()

# Step 6: copy icon
shutil.copyfile(os.path.join(currentPath, "icon.png"),
    os.path.join(currentPath, output, "icon.png"))
shutil.copyfile(os.path.join(currentPath, "icon@2x.png"),
    os.path.join(currentPath, output, "icon@2x.png"))

# Step 7: 打包
if not os.path.exists(os.path.join(currentPath, "dist")):
    os.makedirs(os.path.join(currentPath, "dist"))
tarFile = tarfile.open(os.path.join(currentPath, "dist", tarFileName), "w:gz")
for root, dirNames, fileNames in os.walk(output):
    for fileName in fileNames:
        fullPath = os.path.join(root, fileName)
        print fullPath
        tarFile.add(fullPath)
tarFile.close()

# Step 8: 更新feed url
feedTemplate = Template('''<entry>
    <version>${version}</version>
    <sha1>${sha1Value}</sha1>
    <url>https://raw.githubusercontent.com/magicsky/${appName}/master/dist/${tarFileName}</url>
</entry>''')
fout = open(os.path.join(currentPath, "dist", tarFileName), "rb")
sha1Value = hashlib.sha1(fout.read()).hexdigest()
fout.close()
fin = open(os.path.join(currentPath, feedName), "w")
fin.write(feedTemplate.render(sha1Value = sha1Value, appName = appName, tarFileName = tarFileName, version = version))
fin.close()
