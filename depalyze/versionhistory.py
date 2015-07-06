from __future__ import print_function
import pdb
import pytz
import sys
import json
import dateutil.parser
from dateutil.relativedelta import relativedelta
import re
from collections import defaultdict
import datetime
from timeline.timeline import Timeline
import dateutil
from pointspans import PointSpans

class VersionHistories():
    """Represent the version and dependency history of an entire software ecosystem

     self.dc = name -> version -> date,
     self.dv = name -> version -> import name-> [(type, versionrefstring)]

     self.end_of_time: the last date we have version history data about; e.g. today, if
             dataset is current
    """

    def __init__(self):
        self.dc = {}
        self.dv = {}
        self.depscache = {}
        self.rdepscache = {}
        self.logwith = lambda k: print(k)
        self.end_of_time = datetime.datetime.now().replace(tzinfo=pytz.UTC)

    def serialize(self):
        return {"dc": self.dc, "dv": self.dv, "eot": self.end_of_time}

    def deserialize(self, dct):
        self.preload(dct["dc"], dct["dv"], dct["eot"]) 

    def set_end_of_time(self, end_of_time):
        self.end_of_time = end_of_time
        if self.end_of_time.tzinfo is None:
            self.end_of_time = self.end_of_time.replace(tzinfo=pytz.UTC)

    def force_timezone_awareness(self):
        if self.end_of_time.tzinfo is None:
            self.end_of_time = self.end_of_time.replace(tzinfo=pytz.UTC)
        for p in self.dc:
            for v in self.dc[p]:
                if self.dc[p][v].tzinfo is None:
                    self.dc[p][v] = self.dc[p][v].replace(tzinfo=pytz.UTC)

    def preload(self, dc, dv, end_of_time):
        self.dc = dc
        self.dv = dv
        self.depscache = {}
        self.rdepscache = {}
        self.end_of_time = end_of_time
        self.force_timezone_awareness()

    def logging(self, logfn):
        self.logwith = logfn

    def dep_version_spans(self, package, dep):
        """list of dependency version ref strings, and the timespan over which they were valid"""
        ps = PointSpans()
        for v in self.versions(package):
            if dep in self.dv[package][v] and len(self.dv[package][v][dep]) > 0:
                ps.addchange(self.dv[package][v][dep][0][1], self.dc[package][v])
            else:
                ps.addchange(None, self.dc[package][v])
        return list(ps.foreach(self.end_of_time))

    def buildReverseDependencies(self):
        """Find and cache reverse dependency information

        This is slow, so don't run it if not necessary

        """
        self.rdepscache = defaultdict(set)
        self.rdeptimes = defaultdict(defaultdict)
        self.logwith(str(len(self.dc.keys())) + " packages to process")
        pcount = 0
        for p in self.dc.keys():
            pcount = pcount + 1
            if (pcount % 200 == 0):
                self.logwith("   package #"+ str(pcount)+ ":" + str(p))
            for d in self.dependencies(p):
                self.rdepscache[d].add(p)
                self.rdeptimes[d][p] = self.dep_version_spans(p, d)
        self.logwith("   ...Done with reverse dependencies")

    def versions(self, package):
        """List all known versions of this package"""
        return self.dc[package].keys()

    def dependencies(self, package):
        """List all packages that have ever been dependencies of a package"""
        if package not in self.depscache:
            depset = set()
            for v in self.dv[package]:
                for dep in self.dv[package][v]:
                    depset.add(dep)
            self.depscache[package] = depset 
        return self.depscache[package]

    def showTimeline(self, package, abortIfBoring = False):
        """Textual timeline visualization of versions and dependencies of a package

        Shows version changes to a package, version changes to its dependencies
        and reverse dependencies, and changes to the version numbers specified in
        the dependency links.

        package: the "focal" package to build the visualization around
        returns: yields a list of strings that can be printed out
        """
        self.logwith("Building timeline for"  + str(package))
        if len(self.rdepscache) == 0:
            self.buildReverseDependencies()
        history = []  # (time, column#, text), column = "revdep", "focal", or "dep"
    
        deps = self.dependencies(package)
        revdeps = self.rdeptimes[package].keys()
        self.logwith("Package: " + package)
        for v in self.versions(package):
            history.append((self.dc[package][v], "focal", package + " v" + v))
    
        self.logwith("Dependencies: " + ",".join(deps))
        self.logwith("Reverse Dependencies:" + ",".join(revdeps))
    
        if (abortIfBoring and (len(deps) == 0 or len(revdeps) == 0)):
            raise Exception("uninteresting package: ", package)
    
        for d in deps:
            self.logwith("   Dep: "+ str(d))
            try:
                for depver in self.dc[d]:
                     history.append((self.dc[d][depver], "dep", d + " v" + depver))
            except Exception ,e:
                self.logwith("     No dep info available for " + str(d) + " Error: " + str(e))
            try:
                for (k,st,en) in self.rdeptimes[d][package]:
                     history.append((st, "dep", "ref: " + package + " -> " + d + " v" + k))
                     #history.append((en, "dep", "ref: " + package + " -> " + d + " v" + k + " (end)"))
            except Exception ,e:
                self.logwith("     No2 dep info available for " + str(d) + " Error: " + str(e))
        for r in revdeps:
            self.logwith("   RevDep: "+str(r))
            try:
                for rdepver in self.dc[r]:
                     history.append((self.dc[r][rdepver], "revdep", r + " v" + rdepver))
            except Exception ,e:
                self.logwith("     No reverse dep info available for " + str(d) + "  Error:" + str(e))
            try:
                for (k,st,en) in self.rdeptimes[package][r]:
                     history.append((st, "revdep", "ref: " + r + " -> " + package + " v" + k))
                     #history.append((en, "revdep", "ref: " + r + " -> " + package + " v" + k + " (end)"))
            except Exception ,e:
                self.logwith("     No2 reverse dep info available for " + str(d) + "  Error:" + str(e))
        history = sorted(history, key=lambda (k,c,t): k)
        lasttime = ""
       
        format = "%25s   %20s   %20s   %20s"
        yield format % ("Time", "Dependency changes", package, "Downstream dependencies")
        for (tstamp,colname,text) in history:
            (tempus, tleft, tmid, tright) = ("", "","","")
            tempus = tstamp.strftime("%Y-%m-%d")
            if (tempus == lasttime):
                tempus = ""
            else:
                lasttime = tempus
            if colname == "revdep": tright = text
            if colname == "focal": tmid = text
            if colname == "dep": tleft = text
            yield format % (tempus,tleft,tmid,tright)

    def todo(self):
        """Functions still to be ported from previous implementation

    def allHistories(self):
        (rd, rdt) = buildReverseDependencies()
        for pk in npmKeys(npms):
            try:
                timel = list(showTimeline(pk, rd, rdt))
                pkn = pk.replace("/", "_")
                with open ("timelines/" + pkn + ".timeline.txt", "w") as f:
                    f.write("\n".join(timel))
            except Exception, e:
                print e

    def analyzePackage(package_key, dc, dv):
    
        dcp = dc[p]
        dvp = dv[p]
        print package_key
    
        vers_names = dcp.ketys()
    
        tl = Timeline()
        
    
        # extend each version until the end of hte subsequent version
        for v,w in zip(vers_names, vers_names[1:] + [{"published": today}]):     # Lost author for author color
            tl.span(package_key, d2epoch(dcp[v]), d2epoch(dcp[w]), package_key + ":" + v, v, hashColor(p), None)
    
        for dep in njh.dependencies():
            for (ref,st,en) in njh.dep_version_spans(dep, today):
                tl.span(dep, d2epoch(st), d2epoch(en), dep + "::" + ref, ref, "w", "bottom")
    
            dv = njh.dep_versions(dep)
            try:
                njh2 = NodejsHist(npms, dep)
                vn2 = njh2.versions()
                for vv,ww in zip(vn2, vn2[1:] + [{"published": today}]):
                    tl.span(dep, d2epoch(vv["published"]), d2epoch(ww["published"]), 
                            dep + ":" + vv["key"], vv["key"], hashColor(njh2.author()), "top") 
            except:
                pass
            for vn in vers_names:
                if vn["key"] in dv:
                    dep_ver = extractVersionLimiter(dv[vn["key"]])
                    print dep_ver
                    destrec = tl.findByKey(dep + ":" + dep_ver)
                    srcrec = tl.findByKey(package_key + ":" + vn["key"])
                    if len(destrec) > 0 and len(srcrec) > 0:
                        tl.connect(destrec[0], srcrec[0])
                        print "version", vn["key"], "of", package_key, "did link to dependency", dep, "version", dep_ver
                    else:
                        print "version", vn["key"], "of", package_key, "***can't*** find dependency", \
                               dep, "version", dep_ver, "lendestrec=", len(destrec), "lensrcrec=", len(srcrec)
                else:
                    print "version", vn["key"], "of", package_key, "did not update dependency on", dep
    

        fig, ax = plt.subplots(figsize=(100,max(7, 3*len(tl.categories()))))
        tl.draw_time_axis(ax, limit_view_category=package_key)
        tl.draw_bars(ax)
        tl.draw_connections(ax)
        savefig("plots/" + package_key + ".png")
        """



