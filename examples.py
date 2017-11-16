import json
import depalyze
import dateutil.parser
import pickle
import os.path

#
#  depHistories is assumed to be a directory that caches the DESCRIPTION files
#  of cran projects
#
def demoCran():
    vh = depalyze.scan_R_descriptions("data/depHistories")
    vh.validate()
    for p in vh.interesting_packages():
        vh.dumpVis("plots", p[0])
    print 1.0/vh.average_update_frequency(), "Average days between updates"

def demoEclipse():
    vh = depalyze.scan_eclipse_xml("data/bundledependencies.xml")
    vh.validate()
    for p in vh.interesting_packages():
        vh.dumpVis("plots", p[0])
    print 1.0/vh.average_update_frequency(), "Average days between updates"


# Input file comes from:
#    wget -O /Users/cbogart/data/npmjs.json 'https://skimdb.npmjs.com/registry/_all_docs?include_docs=true'
# which downloads the whole of NPM, boom.

def demoNpm():
    print "Scanning"
    with open("/Users/cbogart/sandbox/npmjson.json", "r") as f:
       vh = depalyze.VersionHistories()
       vh.deserialize(json.loads(f.read(), object_hook=json_util.object_hook))
    #vh = depalyze.scan_npm_json("/users/cbogart/data/npmjs.json")
    #print "Validating"
    #vh.validate()
    print "Plotting"
    for p in vh.interesting_packages()[0:1]:
        vh.dumpVis("plots", p[0])
    print "Averaging"
    print 1.0/vh.average_update_frequency(), "Average days between updates"
    print "Done"
    
demoNpm()

