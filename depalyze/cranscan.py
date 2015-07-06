import os
from rscraper import parseDCF, DCFparse2DependencyLists
import datetime
import pytz
import versionhistory

def scan_R_descriptions(descriptionDir):
    """Turn cache of DESCRIPTION files from R projects over time into dependency data structure"""
    depstruct = []
    for root, dirs, files in os.walk(descriptionDir):
        if len(depstruct) % 500 == 0:
            print "Reading directory", root
        for f in files:
            if f == "DESCRIPTION":
                with open( os.path.join(root,f), "r") as f:
                    depstruct = depstruct + parseDCF(f.read())
    (dc, dv) = DCFparse2DependencyLists(depstruct)
    vh = versionhistory.VersionHistories()
    vh.preload(dc, dv, datetime.datetime.now().replace(tzinfo=pytz.UTC))
    return vh
