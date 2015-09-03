import cranhist
import json
import depalyze
import dateutil.parser
import pickle
import os.path

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


def demoNpm():
    vh = depalyze.scan_npm_json("data/npmjs.json")
    vh.validate()
    for p in vh.interesting_packages():
        vh.dumpVis("plots", p[0])
    print 1.0/vh.average_update_frequency(), "Average days between updates"
    
