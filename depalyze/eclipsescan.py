import os
import datetime
import pytz
import datetime
import versionhistory
from collections import defaultdict
from lxml import objectify

def scan_eclipse_xml(fname, sample = False):
    kidtypes = ["req", "extensionPoint", "extension"]
    ver_changes = dict()
    ver_deps = dict()
    rowcount = 0
    with open(fname,"r") as f:
        for line in f.readlines():
            if len(line) > 2:
                rowcount = rowcount + 1
                if sample and rowcount > 20:
                    break
                try:
                   xmldoc = objectify.fromstring(line.strip())
                   focal = xmldoc.bundle.attrib["name"]
                   focal_ver = xmldoc.bundle.attrib["version"]
                   focal_ver_date = datetime.datetime.fromtimestamp(float(xmldoc.attrib["date"]))
                   if focal not in ver_changes:
                       ver_changes[focal] = dict()
                   if focal not in ver_deps:
                       ver_deps[focal] = dict()
                   if focal_ver not in ver_changes[focal] or ver_changes[focal][focal_ver] < focal_ver_date:
                       ver_changes[focal][focal_ver] = focal_ver_date
                       if focal_ver not in ver_deps[focal]: ver_deps[focal][focal_ver] = dict()
                       for ch in xmldoc.bundle.iterchildren():
                           if "v" in ch.attrib:
                               ver_deps[focal][focal_ver][ch.text] = (ch.tag, ch.attrib["v"])
                           elif "bundle-version" in ch.attrib:
                               ver_deps[focal][focal_ver][ch.text] = (ch.tag, ch.attrib["bundle-version"]) 
                           else:
                               ver_deps[focal][focal_ver][ch.text] = (ch.tag, "")
                except Exception, e:
                   print line, e
    vh = versionhistory.VersionHistories()
    vh.preload(ver_changes, ver_deps, datetime.datetime.now().replace(tzinfo=pytz.UTC))
    return vh


