from matplotlib import scale as mscale
from matplotlib import dates
from matplotlib import textpath
from matplotlib import pyplot

class Timeline:
    #dateformatter = dates.DateFormatter('%m %y')

    def __init__(self):
        self.spans = []
        self.connections = []
        self.loc = dates.AutoDateLocator()
        self.fmt = dates.AutoDateFormatter(self.loc)
        pass

    def findByKey(self,key): 
        return [rec for rec in self.spans if rec["key"] == key]

    def span(self, category, start, end, key, caption, color, half, invisibleBar = False):
        self.spans.append(
            {"cat": category, 
             "start": start,
             "key": key,
             "color": color,
             "end": end,
             "half": half,
             "caption": caption,
             "invisibleBar": invisibleBar})

    def categories(self):
        cats = []
        for sp in self.spans:
            if sp["cat"] not in cats:
                cats.append(sp["cat"])
        return cats

    def timerange(self, filter=lambda sp: True):
        start = min({ sp["start"] for sp in self.spans if filter (sp) })
        end = max({ sp["end"] for sp in self.spans  if filter (sp)})
        return (start, end)

    def xmapping(self):
        return lambda t: t*1.0 

    def ymapping(self, height=500, margins=50, half=None):
        cats = self.categories()
        incr = height*1.0/len(cats)
        print("Yincr = ", incr)
        #catmap = { c : margins+(i*incr) for (i,c) in enumerate(cats) }
        catmap = { c : i for (i,c) in enumerate(cats) }
        def yh(c,h):
            if (h=="top"):      return (catmap[c], catmap[c]+.3)
            elif (h=="bottom"): return (catmap[c]-.3, catmap[c])
            else:               return (catmap[c]-.3,catmap[c]+.3)

        return yh

    def draw_time_axis(self, ax, limit_view_category=None):
        pyplot.rc('font', size=40)
        xf = self.xmapping()
        yf = self.ymapping()
        ax.xaxis.set_major_formatter(self.fmt)
        ax.xaxis.set_major_locator(self.loc)
        ax.yaxis.set_ticks(range(0,len(self.categories())))
        ax.yaxis.set_ticklabels(self.categories())
        if limit_view_category:
            (st,en) = self.timerange(filter=lambda sp: sp["cat"] == limit_view_category)
            #print "Limiting x range to", xf(st), xf(en)
            pyplot.xlim((xf(st), xf(en)))
            self.stretch = xf(en)-xf(st)
            print('TIME RANGE CALC: ', st, en, self.stretch)
        #for label in (ax.get_xticklabels() + ax.get_yticklabels()):
        #    label.set_fontproperties({"size":40})

    def draw_bars(self, ax):
        xf = self.xmapping()
        yf = self.ymapping()
        factor = self.stretch / 4000.0
        print("Factor ",factor,"=" ,self.stretch, "/2000")
        for sp in self.spans:
            if sp["invisibleBar"]:
                ax.bar(xf(sp["start"]),
                       yf(sp["cat"],sp["half"])[1]-yf(sp["cat"],sp["half"])[0],
                       xf(sp["end"]) - xf(sp["start"]),
                       color="white", edgecolor="white",
                       bottom=yf(sp["cat"],sp["half"])[0])
            else:
                ax.bar(xf(sp["start"]),
                       yf(sp["cat"],sp["half"])[1]-yf(sp["cat"],sp["half"])[0],
                       xf(sp["end"]) - xf(sp["start"]),
                       color=sp["color"],
                       bottom=yf(sp["cat"],sp["half"])[0])
            
            if xf(sp["start"]) >= pyplot.xlim()[0] and xf(sp["end"])-xf(sp["start"]) > .5 and sp["caption"] != "":
                t = textpath.TextPath((0,0), " " + sp["caption"], size=40)
                if sp["invisibleBar"]:
                    pyplot.text(sp["start"]+.1, yf(sp["cat"],sp["half"])[1],
                            sp["caption"], ha='left', va='top',
                            rotation=-25, size=20)
                elif t.get_extents().width * factor < xf(sp["end"])-xf(sp["start"]):
                    pyplot.text(xf(sp["start"])+1, yf(sp["cat"],sp["half"])[0]+.05,
                            sp["caption"], ha='left', va='bottom', size=40)
                else:
                    pyplot.text(sp["start"]+.1, yf(sp["cat"],sp["half"])[0]+.05,
                            sp["caption"], ha='left', va='bottom',
                            rotation='vertical', size=16)
            

    def draw_connections(self, ax):
        xf = self.xmapping()
        yf = self.ymapping()
        for (f,t) in self.connections:
            ax.plot([xf(f["start"]),
                     xf(t["start"])],
                    [yf(f["cat"], f["half"])[0], yf(t["cat"], t["half"])[1]],
                    color="r")

                   
    def connect(self, keyfrom, keyto):
        self.connections.append((keyfrom,keyto))


