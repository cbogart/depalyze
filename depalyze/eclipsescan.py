import os
import re
import datetime
import pytz
import datetime
import versionhistory
from collections import defaultdict
from lxml import objectify

repo_comment = re.compile("<!-- ## (.*?)/(.*?) ## -->")

def scan_eclipse_xml(fname, sample = False):
    kidtypes = ["req", "extensionPoint", "extension"]
    ver_changes = dict()
    ver_deps = dict()
    ver_auth = dict()
    bundle2project = defaultdict(set)
    bundle2repo = defaultdict(set)
    bundle2projrepo = defaultdict(set)
    rowcount = 0
    project = ""
    repo = ""
    projrepo = "/"
    with open(fname,"r") as f:
        for line in f.readlines():
            if len(line) > 2:
                rowcount = rowcount + 1
                if sample and rowcount > 20:
                    break
                if "##" in line:
                   projinfo = repo_comment.match(line)
                   if projinfo:
                      project = projinfo.group(1)
                      repo = projinfo.group(2)
                      projrepo = project + "/" + repo
                      print "FOUND: ", projrepo
                      continue
                try:
                   xmldoc = objectify.fromstring(line.strip())
                   focal = xmldoc.bundle.attrib["name"]
                   if projrepo != "":
                       bundle2project[focal].add(project)
                       bundle2repo[focal].add(repo)
                       bundle2projrepo[focal].add(projrepo)
                   if len(focal) == 0: raise ValueError("Empty bundle name; skipping")
                   focal_ver = xmldoc.bundle.attrib["version"]
                   focal_ver_date = datetime.datetime.fromtimestamp(float(xmldoc.attrib["date"]))
                   if focal not in ver_changes:
                       ver_changes[focal] = dict()
                       ver_auth[focal] = ".".join(focal.split(".")[:3])
                   if focal not in ver_deps:
                       ver_deps[focal] = dict()
                   if focal_ver not in ver_changes[focal] or ver_changes[focal][focal_ver] < focal_ver_date:
                       ver_changes[focal][focal_ver] = focal_ver_date
                       if focal_ver not in ver_deps[focal]: ver_deps[focal][focal_ver] = dict()
                       for ch in xmldoc.bundle.iterchildren():
                           if ch.text is None or len(ch.text) == 0:
                               continue
                           if ch.text not in ver_deps[focal][focal_ver]:
                               ver_deps[focal][focal_ver][ch.text] = []
                           if "v" in ch.attrib:
                               ver_deps[focal][focal_ver][ch.text].append((ch.tag, ch.attrib["v"]))
                           elif "bundle-version" in ch.attrib:
                               ver_deps[focal][focal_ver][ch.text].append((ch.tag, ch.attrib["bundle-version"]) )
                           else:
                               ver_deps[focal][focal_ver][ch.text].append((ch.tag, ""))
                except Exception, e:
                   print line, e
    vh = versionhistory.VersionHistories()
    vh.preload(ver_auth, ver_changes, ver_deps, datetime.datetime.now().replace(tzinfo=pytz.UTC))
    
    vh.set_aux("bundle2project", { bundle: list(bundle2project[bundle]) for bundle in bundle2project} )
    vh.set_aux("bundle2repo", { bundle: list(bundle2repo[bundle]) for bundle in bundle2repo} )
    vh.set_aux("bundle2projrepo", { bundle: list(bundle2projrepo[bundle]) for bundle in bundle2projrepo} )
    return vh


