#!/usr/bin/python
# -*- coding: utf-8 -*-

#    NRSC5 DUI - A graphical interface for nrsc5
#    Copyright (C) 2017-2019  Cody Nybo & Clayton Smith, 2019 zefie, 2021 Mark J. Fine
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

#    Updated by zefie for modern nrsc5 ~ 2019
#    Updated and enhanced by markjfine ~ 2021

#import os, sys, shutil, re, gtk, gobject, json, datetime, numpy, glob, time, platform
import os, pty, select, sys, shutil, re, json, datetime, numpy, glob, time, platform
from subprocess import Popen, PIPE
from threading import Timer, Thread
from dateutil import tz
from PIL import Image, ImageFont, ImageDraw

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject, Gdk, GdkPixbuf, GLib

import urllib3
from OpenSSL import SSL

# print debug messages to stdout (if debugger is attached)
debugMessages = (sys.gettrace() != None)
debugAutoStart = True

if hasattr(sys, 'frozen'):
    runtimeDir = os.path.dirname(sys.executable)  # for py2exe
else:
    runtimeDir = sys.path[0]

aasDir = os.path.join(runtimeDir, "aas")  # aas (data from nrsc5) file directory
mapDir = os.path.join(runtimeDir, "map")  # map (data we process) file directory
resDir = os.path.join(runtimeDir, "res")  # resource (application dependencies) file directory
cfgDir = os.path.join(runtimeDir, "cfg")  # config file directory

class NRSC5_DUI(object):
    def __init__(self):
        global runtimeDir, resDir
        #gobject.threads_init()
        #Gdk.threads_init()
        self.windowsOS      = False                             # save our determination as a var in case we change how we determine.

        self.getControls()              # get controls and windows
        self.initStreamInfo()           # initilize stream info and clear status widgets
        self.http = urllib3.PoolManager()

        self.debugLog("Local path determined as " + runtimeDir)

        if (platform.system() == 'Windows'):
            # Windows release layout
            self.windowsOS = True
            self.binDir = os.path.join(runtimeDir, "bin")  # windows binaries directory
            self.nrsc5Path = os.path.join(self.binDir,'nrsc5.exe')
        else:
            # Linux/Mac/proper posix
            # if nrsc5 and transcoder are not in the system path, set the full path here
            arg1 = ""
            if (len(sys.argv[1:]) > 0):
                arg1 = sys.argv[1].strip()
            self.nrsc5Path = arg1+"nrsc5"
 
        self.debugLog("OS Determination: Windows = {}".format(self.windowsOS))

        self.mapFile        = os.path.join(resDir, "map.png")
        self.defaultSize    = [490,250] # default width,height of main app
        self.nrsc5          = None      # nrsc5 process
        self.nrsc5master    = None
        self.nrsc5slave     = None
        self.playerThread   = None      # player thread
        self.playing        = False     # currently playing
        self.statusTimer    = None      # status update timer
        self.imageChanged   = False     # has the album art changed
        self.xhdrChanged    = False     # has the HDDR data changed
        self.nrsc5Args      = []        # arguments for nrsc5
        self.logFile        = None      # nrsc5 log file
        self.lastImage      = ""        # last image file displayed
        self.coverImage     = ""
        self.id3Changed     = False
        #self.lastXHDR       = ["", -1]  # the last XHDR data received
        self.lastXHDR       = ""        # the last XHDR data received
        self.stationStr     = ""        # current station frequency (string)
        self.streamNum      = 0         # current station stream number
        self.nrsc5msg       = ""        # send key command to nrsc5 (streamNum)
        self.update_btns    = True
        self.set_program_btns()
        self.bookmarks      = []        # station bookmarks
        self.booknames      = ["","","",""] # station bookmark names
        self.stationLogos   = {}        # station logos
        self.bookmarked     = False     # is current station bookmarked
        self.mapViewer      = None      # map viewer window
        self.weatherMaps    = []        # list of current weathermaps sorted by time
        self.waittime       = 10        # time in seconds to wait for file to exist
        self.waitdivider    = 4         # check this many times per second for file
        self.pixbuf         = None      # store image buffer for rescaling on resize
        self.mimeTypes      = {         # as defined by iHeartRadio anyway, defined here for possible future use
            "4F328CA0":["image/png","png"],
            "1E653E9C":["image/jpg","jpg"],
            "BB492AAC":["text/plain","txt"]
        }
        self.mapData        = {
            "mapMode"       : 1,
            "mapTiles"      : [[0,0,0],[0,0,0],[0,0,0]],
            "mapComplete"   : False,
            "weatherTime"   : 0,
            "weatherPos"    : [0,0,0,0],
            "weatherNow"    : "",
            "weatherID"     : "",
            "viewerConfig"  : {
                "mode"           : 1,
                "animate"        : False,
                "scale"          : True,
                "windowPos"      : (0,0),
                "windowSize"     : (764,632),
                "animationSpeed" : 0.5
            }
        }

        self.ServiceDataType = {
            0 : "Non_Specific",            
            1 : "News",                     
            3 : "Sports",                   
            29 : "Weather",                  
            31 : "Emergency",                
            65 : "Traffic",                  
            66 : "Image Maps",               
            80 : "Text",                     
            256 : "Advertising",              
            257 : "Financial",                
            258 : "Stock Ticker",             
            259 : "Navigation",               
            260 : "Electronic Program Guide", 
            261 : "Audio",                    
            262 : "Private Data Network",     
            263 : "Service Maintenance",      
            264 : "HD Radio System Services", 
            265 : "Audio-Related Objects",       
            511 : "Test_Str_E"               
        }

        self.ProgramType = {
            0 : "None",
            1 : "News",
            2 : "Information",
            3 : "Sports",
            4 : "Talk",
            5 : "Rock",
            6 : "Classic Rock",
            7 : "Adult Hits",
            8 : "Soft Rock",
            9 : "Top 40",
            10 : "Country",
            11 : "Oldies",
            12 : "Soft",
            13 : "Nostalgia",
            14 : "Jazz",
            15 : "Classical",
            16 : "Rhythm and Blues",
            17 : "Soft Rhythm and Blues",
            18 : "Foreign Language",
            19 : "Religious Music",
            20 : "Religious Talk",
            21 : "Personality",
            22 : "Public",
            23 : "College",
            24 : "Spanish Talk",
            25 : "Spanish Music",
            26 : "Hip-Hop",
            29 : "Weather",
            30 : "Emergency Test",
            31 : "Emergency",
            65 : "Traffic",
            76 : "Special Reading Services"
        }

        self.pointer_cursor = Gdk.Cursor(Gdk.CursorType.LEFT_PTR)
        self.hand_cursor = Gdk.Cursor(Gdk.CursorType.HAND2)
        #self.missing_image = Gtk.Image.new_from_icon_name("MISSING_IMAGE",Gtk.IconSize.LARGE_TOOLBAR)

        # set events on info labels
        self.set_tuning_actions(self.btnAudioPrgs0, "btn_prg0", False, False)
        self.set_tuning_actions(self.btnAudioPrgs1, "btn_prg1", False, False)
        self.set_tuning_actions(self.btnAudioPrgs2, "btn_prg2", False, False)
        self.set_tuning_actions(self.btnAudioPrgs3, "btn_prg3", False, False)

        self.set_tuning_actions(self.lblAudioPrgs0, "prg0", True, True)
        self.set_tuning_actions(self.lblAudioPrgs1, "prg1", True, True)
        self.set_tuning_actions(self.lblAudioPrgs2, "prg2", True, True)
        self.set_tuning_actions(self.lblAudioPrgs3, "prg3", True, True)

        self.set_tuning_actions(self.lblAudioSvcs0, "svc0", True, True)
        self.set_tuning_actions(self.lblAudioSvcs1, "svc1", True, True)
        self.set_tuning_actions(self.lblAudioSvcs2, "svc2", True, True)
        self.set_tuning_actions(self.lblAudioSvcs3, "svc3", True, True)

        # setup bookmarks listview
        nameRenderer = Gtk.CellRendererText()
        nameRenderer.set_property("editable", True)
        nameRenderer.connect("edited", self.on_bookmarkNameEdited)
        
        colStation = Gtk.TreeViewColumn("Station", Gtk.CellRendererText(), text=0)
        colName    = Gtk.TreeViewColumn("Name", nameRenderer, text=1)

        colStation.set_resizable(True)
        colStation.set_sort_column_id(2)
        colName.set_resizable(True)
        colName.set_sort_column_id(1)
        
        self.lvBookmarks.append_column(colStation)
        self.lvBookmarks.append_column(colName)
        
        # regex for getting nrsc5 output
        self.regex = [
            #re.compile("^.*main\.c:[\d]+: Station name: (.*)$"),                                                    #  0 match station name
            #re.compile("^.*main\.c:[\d]+: Station location: (-?[\d]+\.[\d]+) (-?[\d]+\.[\d]+), ([\d]+)m$"),         #  1 match station location
            #re.compile("^.*main\.c:[\d]+: Slogan: (.*)$"),                                                          #  2 match station slogan
            #re.compile("^.*main\.c:[\d]+: Audio bit rate: (.*) kbps$"),                                           #  3 match audio bit rate
            #re.compile("^.*main\.c:[\d]+: Title: (.*)$"),                                                         #  4 match title
            #re.compile("^.*main\.c:[\d]+: Artist: (.*)$"),                                                        #  5 match artist
            #re.compile("^.*main\.c:[\d]+: Album: (.*)$"),                                                         #  6 match album
            #re.compile("^.*main\.c:[\d]+: LOT file: port=([\d]+) lot=([\d]+) name=(.*\.(?:jpg|png|txt)) size=([\d]+) mime=([\w]+)$"),               #  7 match file (album art, maps, weather info)
            #re.compile("^.*main\.c:[\d]+: MER: (-?[\d]+\.[\d]+) dB \(lower\), (-?[\d]+\.[\d]+) dB \(upper\)$"),     #  8 match MER
            #re.compile("^.*main\.c:[\d]+: BER: (0\.[\d]+), avg: (0\.[\d]+), min: (0\.[\d]+), max: (0\.[\d]+)$"),  #  9 match BER
            #re.compile("^.*nrsc5\.c:[\d]+: Best gain: (.*) dB,.*$"),                                                       # 10 match gain
            #re.compile("^.*main\.c:[\d]+: SIG Service: type=(.*) number=(.*) name=(.*)$"), # 11 match stream
            #re.compile("^.*main\.c:[\d]+: .*Data component:.* port=([\d]+).* type=([\d]+) .*$"),                     # 12 match port
            #re.compile("^.*main\.c:[\d]+: XHDR: .* ([0-9A-Fa-f]{8}) (.*)$"),                                 # 13 match xhdr tag
            #re.compile("^.*main\.c:[\d]+: Unique file identifier: PPC;07; ([\S]+).*$")                            # 14 match unique file id
            re.compile("^[0-9\:]{8,8} Station name: (.*)$"),                                                    #  0 match station name
            re.compile("^[0-9\:]{8,8} Station location: (-?[\d]+\.[\d]+) (-?[\d]+\.[\d]+), ([\d]+)m$"),         #  1 match station location
            re.compile("^[0-9\:]{8,8} Slogan: (.*)$"),                                                          #  2 match station slogan
            re.compile("^[0-9\:]{8,8} Audio bit rate: (.*) kbps$"),                                             #  3 match audio bit rate
            re.compile("^[0-9\:]{8,8} Title: (.*)$"),                                                           #  4 match title
            re.compile("^[0-9\:]{8,8} Artist: (.*)$"),                                                          #  5 match artist
            re.compile("^[0-9\:]{8,8} Album: (.*)$"),                                                           #  6 match album
            re.compile("^[0-9\:]{8,8} LOT file: port=([\d]+) lot=([\d]+) name=(.*\.(?:jpg|png|txt)) size=([\d]+) mime=([\w]+)$"), #  7 match file (album art, maps, weather info)
            re.compile("^[0-9\:]{8,8} MER: (-?[\d]+\.[\d]+) dB \(lower\), (-?[\d]+\.[\d]+) dB \(upper\)$"),     #  8 match MER
            re.compile("^[0-9\:]{8,8} BER: (0\.[\d]+), avg: (0\.[\d]+), min: (0\.[\d]+), max: (0\.[\d]+)$"),    #  9 match BER
            re.compile("^[0-9\:]{8,8} Best gain: (.*) dB,.*$"),                                                 # 10 match gain
            re.compile("^[0-9\:]{8,8} SIG Service: type=(.*) number=(.*) name=(.*)$"),                          # 11 match stream
            re.compile("^[0-9\:]{8,8} .*Data component:.* id=([\d]+).* port=([\d]+).* service_data_type=([\d]+) .*$"), # 12 match port (and data_service_type)
            re.compile("^[0-9\:]{8,8} XHDR: (.*) ([0-9A-Fa-f]{8}) (.*)$"),                                      # 13 match xhdr tag
            re.compile("^[0-9\:]{8,8} Unique file identifier: PPC;07; ([\S]+).*$"),                             # 14 match unique file id
            re.compile("^[0-9\:]{8,8} Genre: (.*)$"),                                                           # 15 match genre
            re.compile("^[0-9\:]{8,8} Message: (.*)$"),                                                         # 16 match message
            re.compile("^[0-9\:]{8,8} Alert: (.*)$"),                                                           # 17 match alert
            re.compile("^[0-9\:]{8,8} .*Audio component:.* id=([\d]+).* port=([\d]+).* type=([\d]+) .*$"),      # 18 match port (and type)
            re.compile("^[0-9\:]{8,8} Synchronized$"),                                                          # 19 synchronized
            re.compile("^[0-9\:]{8,8} Lost synchronization$"),                                                  # 20 lost synch
            re.compile("^[0-9\:]{8,8} Lost device$"),                                                           # 21 lost device
            re.compile("^[0-9\:]{8,8} Open device failed.$")                                                    # 22 No device
        ]
        
        self.loadSettings()
        self.proccessWeatherMaps()
        #self..connect('check-resize',self.on_window_resized) # TODO: fix on resize infinite loop
        
        # set up pty
        self.nrsc5master,self.nrsc5slave = pty.openpty()

    def set_tuning_actions(self, widget, name, has_win, set_curs):
        widget.set_property("name",name)
        widget.set_sensitive(False)
        if has_win:
            widget.set_has_window(True)
        widget.set_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        widget.connect("button-press-event", self.on_program_select)
        if set_curs:
            widget.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK)
            widget.connect("enter-notify-event", self.on_enter_set_cursor)

    def on_enter_set_cursor(self, widget, event):
        if (widget.get_label() != ""):
            widget.get_window().set_cursor(self.hand_cursor)

    def img_to_pixbuf(self,img):
        """convert PIL.Image to GdkPixbuf.Pixbuf"""
        data = GLib.Bytes.new(img.tobytes())
        return GdkPixbuf.Pixbuf.new_from_bytes(data, GdkPixbuf.Colorspace.RGB, 'A' in img.getbands(),8, img.width, img.height, len(img.getbands())*img.width)

    def on_cover_resize(self, container):
        global mapDir
        if self.coverImage != "":
            #img_size = min(self.alignmentCover.get_allocated_height(), self.alignmentCover.get_allocated_width()) - 12
            #pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.coverImage)
            #pixbuf = pixbuf.scale_simple(img_size, img_size, GdkPixbuf.InterpType.BILINEAR)
            #self.imgCover.set_from_pixbuf(pixbuf)
            self.showArtwork(self.coverImage)

        img_size = min(self.alignmentMap.get_allocated_height(), self.alignmentMap.get_allocated_width()) - 12           
        if (self.mapData["mapMode"] == 0):
            map_file = os.path.join(mapDir, "TrafficMap.png")
            if os.path.isfile(map_file):
                map_img = Image.open(map_file).resize((img_size, img_size), Image.LANCZOS)
                self.imgMap.set_from_pixbuf(self.img_to_pixbuf(map_img))
            else:
                #self.imgMap.set_from_stock(Gtk.STOCK_MISSING_IMAGE, Gtk.IconSize.LARGE_TOOLBAR)
                self.imgMap.set_from_icon_name("MISSING_IMAGE", Gtk.IconSize.DIALOG)
        elif (self.mapData["mapMode"] == 1):
            if os.path.isfile(self.mapData["weatherNow"]):
                map_img = Image.open(self.mapData["weatherNow"]).resize((img_size, img_size), Image.LANCZOS)
                self.imgMap.set_from_pixbuf(self.img_to_pixbuf(map_img))
            else:
                #self.imgMap.set_from_stock(Gtk.STOCK_MISSING_IMAGE, Gtk.IconSize.LARGE_TOOLBAR)
                self.imgMap.set_from_icon_name("MISSING_IMAGE", Gtk.IconSize.DIALOG)

    def id3_did_change(self):
        oldTitle = self.txtTitle.get_label()
        oldArtist = self.txtArtist.get_label()
        newTitle = self.streamInfo["Title"]
        newArtist = self.streamInfo["Artist"]
        return ((newArtist != oldArtist) and (newTitle != oldTitle))

    def get_cover_data(self, response):
        check = -1
        resultUrl = ""
        resultArtist = ""
        m = re.search(r"card card_large float_fix",response)
        if (m.start() > -1):
           response = response[m.start():]
           m = re.search(r"<img data-src=\"",response)
           if (m.start() > -1):
               response = response[m.start()+15:]
               m = re.search(r"\"",response)
               if (m.start() > -1):
                   resultUrl = response[:m.start()]
                   response = response[m.start()+1:]
                   m = re.search(r"<span title=\"",response)
                   if (m.start() > -1):
                       response = response[m.start()+13:]
                       m = re.search(r"\"",response)
                       if (m.start() > -1):
                           resultArtist = response[:m.start()]
                           response = response[m.start()+1:]
                           check = 0
        return check, response, resultUrl, resultArtist
        
    def fix_artist(self):
        newArtist = self.streamInfo["Artist"]
        if ("/" in newArtist):
            m = re.search(r"/",newArtist)
            if (m.start() > -1):
                newArtist = newArtist[:m.start()].strip()
        return newArtist

    def get_cover_image_online(self):
        global aasDir
        got_cover = False

        # only change when there's a new ID3
        if (self.id3Changed):
            # only care about the first artist listed if separated by slashes
            newArtist = self.fix_artist()
            baseStr = str(newArtist +" - "+self.streamInfo["Title"]).replace("/","_").replace(":","_")
            #saveStr = "aas/"+ baseStr.replace(" ","_")+".jpg"
            saveStr = os.path.join(aasDir, baseStr.replace(" ","_")+".jpg")
            searchStr = baseStr.replace(" ","+")

            # does it already exist?
            if (os.path.isfile(saveStr)):
                self.coverImage = saveStr

            # if not, get it from Discogs
            else:
                try:
                    searchStr = "https://www.discogs.com/search/?q="+searchStr+"&type=all"
                    r = self.http.request('GET',searchStr)
                    if (r.status == 200):
                        response = r.data.decode('utf-8')

                        # loop through the page until you either get an artist match or you run out of page (check)
                        while (not got_cover):
                            resultUrl = ""
                            resultArtist = ""
                            check, response, resultUrl, resultArtist = self.get_cover_data(response)
                            got_cover = (newArtist.lower() in resultArtist.lower()) and (check == 0)
                        
                        # if you got a match, save it
                        if (resultUrl != ""):
                            with self.http.request('GET', resultUrl, preload_content=False) as r, open(saveStr, 'wb') as out_file:       
                                if (r.status == 200):
                                    shutil.copyfileobj(r, out_file)
                                    self.coverImage = saveStr

                        # If no match use the station logo if there is one
                        else:
                            self.coverImage = os.path.join(aasDir, self.stationLogos[self.stationStr][self.streamNum])
                except:
                    pass

            # now display it by simulating a window resize
            self.on_cover_resize(self.mainWindow)

    def showArtwork(self, art):
        img_size = min(self.alignmentCover.get_allocated_height(), self.alignmentCover.get_allocated_width()) - 12
        self.pixbuf = GdkPixbuf.Pixbuf.new_from_file(art)
        self.pixbuf = self.pixbuf.scale_simple(img_size, img_size, GdkPixbuf.InterpType.BILINEAR)
        self.imgCover.set_from_pixbuf(self.pixbuf)

    def displayLogo(self):
        global aasDir
        #if (self.stationLogos.has_key(self.stationStr)):
        if (self.stationStr in self.stationLogos):
            # show station logo if it's cached
            logo = os.path.join(aasDir, self.stationLogos[self.stationStr][self.streamNum])
            if (os.path.isfile(logo)):
                self.streamInfo["Logo"] = self.stationLogos[self.stationStr][self.streamNum]
                #img_size = min(self.alignmentCover.get_allocated_height(), self.alignmentCover.get_allocated_width()) - 12
                #self.pixbuf = Gtk.gdk.pixbuf_new_from_file(logo)
                #self.pixbuf = GdkPixbuf.Pixbuf.new_from_file(logo)
                self.coverImage = logo
                #self.handle_window_resize()
                #self.pixbuf = self.pixbuf.scale_simple(img_size, img_size, GdkPixbuf.InterpType.BILINEAR)
                #self.imgCover.set_from_pixbuf(self.pixbuf)
                self.showArtwork(logo)
        else:
            # add entry in database for the station if it doesn't exist
            self.stationLogos[self.stationStr] = ["", "", "", ""]

    def service_data_type_name(self, type):
        for key, value in self.ServiceDataType.items():
            if (key == type):
               return value

    def program_type_name(self, type):
        for key, value in self.ProgramType.items():
            if (key == type):
               return value

    def handle_window_resize(self):
        if (self.pixbuf != None):
            #allocation = self.imgCover.get_allocation()
            #desired_width = int(allocation.width / 2.5)
            #desired_height = desired_width
            desired_size = min(self.alignmentCover.get_allocated_height(), self.alignmentCover.get_allocated_width()) - 12
            #self.pixbuf = self.pixbuf.scale_simple(desired_width, desired_height, Gtk.gdk.INTERP_HYPER)
            self.pixbuf = self.pixbuf.scale_simple(desired_size, desired_size, GdkPixbuf.InterpType.BILINEAR)
            self.imgCover.set_from_pixbuf(self.pixbuf)

    def on_window_resized(self,window):
        self.handle_window_resize()

    def on_btnPlay_clicked(self, btn):
        global aasDir
        # start playback
        if (not self.playing):

            self.nrsc5Args = [self.nrsc5Path]
            
            # update all of the spin buttons to prevent the text from sticking 
            self.spinFreq.update()
            #self.spinStream.update()
            self.spinGain.update()
            self.spinPPM.update()
            self.spinRTL.update()
            
            # enable aas output if temp dir was created
            if (aasDir is not None):
                self.nrsc5Args.append("--dump-aas-files")
                self.nrsc5Args.append(aasDir)
            
            # set gain if auto gain is not selected
            if (not self.cbAutoGain.get_active()):
                self.streamInfo["Gain"] = self.spinGain.get_value()
                self.nrsc5Args.append("-g")
                #self.nrsc5Args.append(str(int(self.streamInfo["Gain"]*10)))
                self.nrsc5Args.append(str(int(self.streamInfo["Gain"])))
            
            # set ppm error if not zero
            if (self.spinPPM.get_value() != 0):
                self.nrsc5Args.append("-p")
                self.nrsc5Args.append(str(int(self.spinPPM.get_value())))
            
            # set rtl device number if not zero
            if (self.spinRTL.get_value() != 0):
                self.nrsc5Args.append("-d")
                self.nrsc5Args.append(str(int(self.spinRTL.get_value())))
            
            # set frequency and stream
            self.nrsc5Args.append(str(self.spinFreq.get_value()))
            #self.nrsc5Args.append(str(int(self.spinStream.get_value()-1)))
            self.nrsc5Args.append(str(int(self.streamNum)))
                        
            #print(self.nrsc5Args)

            # start the timer
            self.statusTimer = Timer(1, self.checkStatus)
            self.statusTimer.start()
            
            # disable the controls
            self.spinFreq.set_sensitive(False)
            #self.spinStream.set_sensitive(False)
            self.spinGain.set_sensitive(False)
            self.spinPPM.set_sensitive(False)
            self.spinRTL.set_sensitive(False)
            self.btnPlay.set_sensitive(False)
            self.btnStop.set_sensitive(True)
            self.cbAutoGain.set_sensitive(False)
            self.playing = True
            #self.lastXHDR = ["", -1]
            self.lastXHDR = ""
            
            # start the player thread
            self.playerThread = Thread(target=self.play)
            self.playerThread.start()
            
            self.stationStr = str(self.spinFreq.get_value())
            #self.stationNum = int(self.spinStream.get_value())-1
            #self.set_program_btns()

            self.displayLogo()         
            
            # check if station is bookmarked
            self.bookmarked = False
            #freq = int((self.spinFreq.get_value()+0.005)*100) + int(self.spinStream.get_value())
            freq = int((self.spinFreq.get_value()+0.005)*100) + int(self.streamNum + 1)
            for b in self.bookmarks:
                if (b[2] == freq):
                    self.bookmarked = True
                    break

            self.get_bookmark_names()

            self.btnBookmark.set_sensitive(not self.bookmarked)
            if (self.notebookMain.get_current_page() != 3):
                self.btnDelete.set_sensitive(self.bookmarked)
    
    def get_bookmark_names(self):
        self.booknames = ["","","",""]
        freq = str(int((self.spinFreq.get_value()+0.005)*10))
        for b in self.bookmarks:
            test = str(b[2])
            if (test[:-1] == freq):
                self.booknames[int(test[-1])-1] = b[1]

    def on_btnStop_clicked(self, btn):
        # stop playback
        if (self.playing):
            self.playing = False
            
            # shutdown nrsc5 
            if (self.nrsc5 is not None and not self.nrsc5.poll()):
                self.nrsc5.terminate()
            
            if (self.playerThread is not None) and (btn is not None):
                self.playerThread.join(1)
            
            # stop timer
            self.statusTimer.cancel()
            self.statusTimer = None
            
            # enable controls
            if (not self.cbAutoGain.get_active()):
                self.spinGain.set_sensitive(True)
            self.spinFreq.set_sensitive(True)
            #self.spinStream.set_sensitive(True)
            self.spinPPM.set_sensitive(True)
            self.spinRTL.set_sensitive(True)
            self.btnPlay.set_sensitive(True)
            self.btnStop.set_sensitive(False)
            self.btnBookmark.set_sensitive(False)
            self.cbAutoGain.set_sensitive(True)
            
            # clear stream info
            self.initStreamInfo()
            
            self.btnBookmark.set_sensitive(False)
            if (self.notebookMain.get_current_page() != 3):
                self.btnDelete.set_sensitive(False)

    def on_btnBookmark_clicked(self, btn):         
        # pack frequency and channel number into one int
        #freq = int((self.spinFreq.get_value()+0.005)*100) + int(self.spinStream.get_value())
        freq = int((self.spinFreq.get_value()+0.005)*100) + int(self.streamNum + 1)
        
        # create bookmark
        bookmark = [
            #"{:4.1f}-{:1.0f}".format(self.spinFreq.get_value(), self.spinStream.get_value()),
            "{:4.1f}-{:1.0f}".format(self.spinFreq.get_value(), self.streamNum + 1),
            self.streamInfo["Callsign"],
            freq
        ]
        self.bookmarked = True                  # mark as bookmarked
        self.bookmarks.append(bookmark)         # store bookmark in array
        self.lsBookmarks.append(bookmark)       # add bookmark to listview
        self.btnBookmark.set_sensitive(False)   # disable bookmark button
        
        if (self.notebookMain.get_current_page() != 3):
            self.btnDelete.set_sensitive(True)  # enable delete button

        self.get_bookmark_names()

    def on_btnDelete_clicked(self, btn):
        # select current station if not on bookmarks page
        if (self.notebookMain.get_current_page() != 3):
            station = int((self.spinFreq.get_value()+0.005)*100) + int(self.streamNum + 1)
            for i in range(0, len(self.lsBookmarks)):
                if (self.lsBookmarks[i][2] == station):            
                    self.lvBookmarks.set_cursor(i)
                    break
        
        # get station of selected row
        (model, iter) = self.lvBookmarks.get_selection().get_selected()
        station = model.get_value(iter, 2)
        
        # remove row
        model.remove(iter)
        
        # remove bookmark
        for i in range(0, len(self.bookmarks)):
            if (self.bookmarks[i][2] == station):
                self.bookmarks.pop(i)
                break
        
        if (self.notebookMain.get_current_page() != 3 and self.playing):
            self.btnBookmark.set_sensitive(True)
            self.bookmarked = False

        self.get_bookmark_names()

    def on_btnAbout_activate(self, btn):
        global resDir
        # sets up and displays about dialog
        if self.about_dialog:
            self.about_dialog.present()
            return

        authors = [
            "Cody Nybo <cmnybo@gmail.com>",
            "Clayton Smith <argilo@gmail.com>",
            "nefie <zefie@zefie.net>",
            "Mark J. Fine <mark.fine@fineware-swl.com>"
        ]

        license = """
        NRSC5 DUI - A second-generation graphical interface for nrsc5
        Copyright (C) 2017-2019  Cody Nybo & Clayton Smith, 2019 zefie, 2021 Mark J. Fine
        This program is free software: you can redistribute it and/or modify
        it under the terms of the GNU General Public License as published by
        the Free Software Foundation, either version 3 of the License, or
        (at your option) any later version.
        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU General Public License for more details.
        You should have received a copy of the GNU General Public License
        along with this program.  If not, see <http://www.gnu.org/licenses/>."""

        about_dialog = Gtk.AboutDialog()
        about_dialog.set_transient_for(self.mainWindow)
        about_dialog.set_destroy_with_parent(True)
        about_dialog.set_name("NRSC5 DUI")
        about_dialog.set_program_name("NRSC5 DUI")
        about_dialog.set_version("2.1.0")
        about_dialog.set_copyright("Copyright © 2017-2019 Cody Nybo & Clayton Smith, 2019 zefie, 2021 Mark J. Fine")
        about_dialog.set_website("https://github.com/markjfine/nrsc5-dui")
        about_dialog.set_comments("A second-generation graphical interface for nrsc5.")
        about_dialog.set_authors(authors)
        about_dialog.set_license(license)
        #about_dialog.set_logo(Gtk.gdk.pixbuf_new_from_file("logo.png"))
        about_dialog.set_logo(GdkPixbuf.Pixbuf.new_from_file(os.path.join(resDir,"logo.png")))

        # callbacks for destroying the dialog
        def close(dialog, response, editor):
            editor.about_dialog = None
            dialog.destroy()

        def delete_event(dialog, event, editor):
            editor.about_dialog = None
            return True

        about_dialog.connect("response", close, self)
        about_dialog.connect("delete-event", delete_event, self)

        self.about_dialog = about_dialog
        about_dialog.show()

    def on_stream_changed(self):
        self.lastXHDR = ""
        self.streamInfo["Title"] = ""
        self.streamInfo["Album"] = ""
        self.streamInfo["Artist"] = ""
        self.streamInfo["Genre"] = ""
        self.streamInfo["Cover"] = ""
        self.streamInfo["Logo"] = ""
        self.streamInfo["Bitrate"] = 0
        self.set_program_btns()
        if self.playing:
            self.nrsc5msg = str(self.streamNum)
            self.displayLogo()
        #TODO: fix so stream change is smoother - should be able to pipe new stream number to running application and update display_logo()
        #      For now, just restart
        #if (self.playing):
        #     self.on_btnStop_clicked(None)
        #     self.on_btnPlay_clicked(None)        

    def set_program_btns(self):
        self.btnAudioPrgs0.set_active(self.update_btns and self.streamNum == 0)
        self.btnAudioPrgs1.set_active(self.update_btns and self.streamNum == 1)
        self.btnAudioPrgs2.set_active(self.update_btns and self.streamNum == 2)
        self.btnAudioPrgs3.set_active(self.update_btns and self.streamNum == 3)
        self.update_btns = True

    def on_program_select(self, _label, evt):
        stream_num = int(_label.get_property("name")[-1])
        is_lbl = _label.get_property("name")[0] != "b"
        self.update_btns = is_lbl
        self.streamNum = stream_num
        self.on_stream_changed()

    def on_cbAutoGain_toggled(self, btn):
        self.spinGain.set_sensitive(not btn.get_active())
        self.lblGain.set_visible(btn.get_active())

    def on_listviewBookmarks_row_activated(self, treeview, path, view_column):
        if (len(path) != 0):
            # get station from bookmark row
            tree_iter = treeview.get_model().get_iter(path[0])
            station   = treeview.get_model().get_value(tree_iter, 2)
            
            # set frequency and stream
            self.spinFreq.set_value(float(int(station/10)/10.0))
            #self.spinStream.set_value(station%10)
            self.streamNum = (station%10)-1
            self.on_stream_changed()
            
            # stop playback if playing
            if (self.playing):
                 self.on_btnStop_clicked(None)
            
            # play bookmarked station
            self.on_btnPlay_clicked(None)

    def on_lvBookmarks_selection_changed(self, tree_selection):
        # enable delete button if bookmark is selected
        (model, pathlist) = self.lvBookmarks.get_selection().get_selected_rows()
        self.btnDelete.set_sensitive(len(pathlist) != 0)

    def on_bookmarkNameEdited(self, cell, path, text, data=None):
        # update name in listview
        iter = self.lsBookmarks.get_iter(path)
        self.lsBookmarks.set(iter, 1, text)
        
        # update name in bookmarks array
        for b in self.bookmarks:
            if (b[2] == self.lsBookmarks[path][2]):
                b[1] = text
                break

    def on_notebookMain_switch_page(self, notebook, page, page_num):
        # disable delete button if not on bookmarks page and station is not bookmarked
        if (page_num != 3 and (not self.bookmarked or not self.playing)):
            self.btnDelete.set_sensitive(False)
        # enable delete button if not on bookmarks page and station is bookmarked
        elif (page_num != 3 and self.bookmarked):
            self.btnDelete.set_sensitive(True)
        # enable delete button if on bookmarks page and a bookmark is selected
        else:
            (model, iter) = self.lvBookmarks.get_selection().get_selected()
            self.btnDelete.set_sensitive(iter is not None)
    
    def on_radMap_toggled(self, btn):
        global mapDir
        if (btn.get_active()):
            if (btn == self.radMapTraffic):
                self.mapData["mapMode"] = 0
                mapFile = os.path.join(mapDir, "TrafficMap.png")
                if (os.path.isfile(mapFile)):                                                           # check if map exists
                    mapImg = Image.open(mapFile).resize((200,200), Image.LANCZOS)                       # scale map to fit window
                    self.imgMap.set_from_pixbuf(imgToPixbuf(mapImg))                                    # convert image to pixbuf and display
                else:
                    #self.imgMap.set_from_stock(Gtk.STOCK_MISSING_IMAGE, Gtk.ICON_SIZE_LARGE_TOOLBAR)    # display missing image if file is not found
                    #self.imgMap.set_from_stock(Gtk.STOCK_MISSING_IMAGE, Gtk.IconSize.LARGE_TOOLBAR)    # display missing image if file is not found
                    self.imgMap.set_from_icon_name("MISSING_IMAGE", Gtk.IconSize.DIALOG)
            
            elif (btn == self.radMapWeather):
                self.mapData["mapMode"] = 1
                if (os.path.isfile(self.mapData["weatherNow"])):
                    mapImg = Image.open(self.mapData["weatherNow"]).resize((200,200), Image.LANCZOS)    # scale map to fit window
                    self.imgMap.set_from_pixbuf(imgToPixbuf(mapImg))                                    # convert image to pixbuf and display 
                else:
                    #self.imgMap.set_from_stock(Gtk.STOCK_MISSING_IMAGE, Gtk.ICON_SIZE_LARGE_TOOLBAR)    # display missing image if file is not found
                    #self.imgMap.set_from_stock(Gtk.STOCK_MISSING_IMAGE, Gtk.IconSize.LARGE_TOOLBAR)    # display missing image if file is not found
                    self.imgMap.set_from_icon_name("MISSING_IMAGE", Gtk.IconSize.DIALOG)
    
    def on_btnMap_clicked(self, btn):
        # open map viewer window
        if (self.mapViewer is None):
            self.mapViewer = NRSC5_Map(self, self.mapViewerCallback, self.mapData)
            self.mapViewer.mapWindow.show()
    
    def mapViewerCallback(self):
        # delete the map viewer
        self.mapViewer = None
    
    def play(self):
        FNULL = open(os.devnull, 'w')
        FTMP = open('tmp.log','w')

        # run nrsc5 and output stdout & stderr to pipes
        #self.nrsc5 = Popen(self.nrsc5Args, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        self.nrsc5 = Popen(self.nrsc5Args, shell=False, stdin=self.nrsc5slave, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        
        while True:
            # send input to nrsc5 if needed
            if (self.nrsc5msg != ""):
                select.select([],[self.nrsc5master],[])
                os.write(self.nrsc5master,str.encode(self.nrsc5msg))
                #print(self.nrsc5msg)
                self.nrsc5msg = ""
            # read output from nrsc5
            output = self.nrsc5.stderr.readline()
            # parse the output
            self.parseFeedback(output)
            
            # write output to log file if enabled
            if (self.cbLog.get_active() and self.logFile is not None):
                self.logFile.write(output)
                self.logFile.flush()
            
            # check if nrsc5 has exited
            if (self.nrsc5.poll() and not self.playing):
                # cleanup if shutdown
                self.debugLog("Process Terminated")
                self.nrsc5 = None
                break
            elif (self.nrsc5.poll() and self.playing):
                # restart nrsc5 if it crashes
                self.debugLog("Restarting NRSC5")
                time.sleep(1)
                self.nrsc5 = Popen(self.nrsc5Args, shell=False, stdin=self.nrsc5slave, stdout=PIPE, stderr=PIPE, universal_newlines=True)

    def set_synchronization(self, state):
        self.imgNoSynch.set_visible(state == 0)
        self.imgSynch.set_visible(state == 1)
        self.imgLostDevice.set_visible(state == -1)

    def set_button_name(self, btnWidget, lblWidget, stream):
        temp = self.streamInfo["Streams"][stream]
        if ((temp == "") or (temp == "MPS") or (temp[0:3] == "SPS") or (temp[0:2] == "HD") ):
            if (self.booknames[stream] != ""):
                temp = self.booknames[stream]
        lblWidget.set_label(temp)
        btnWidget.set_sensitive(temp != "")

    def set_label_name(self, lblWidget, inString, doSens):
        lblWidget.set_label(inString)
        lblWidget.set_tooltip_text(inString)
        if (doSens):
            lblWidget.set_sensitive(inString != "")

    def checkStatus(self):
        # update status information
        def update():
            global aasDir
            #Gdk.threads_enter()
            try:
                imagePath = ""
                image = ""
                #ber = [self.streamInfo["BER"][0]*100,self.streamInfo["BER"][1]*100,self.streamInfo["BER"][2]*100,self.streamInfo["BER"][3]*100]
                ber = [self.streamInfo["BER"][i]*100 for i in range(4)]
                self.id3Changed = self.id3_did_change()
                self.txtTitle.set_text(self.streamInfo["Title"])
                self.txtTitle.set_tooltip_text(self.streamInfo["Title"])
                self.txtArtist.set_text(self.streamInfo["Artist"])
                self.txtArtist.set_tooltip_text(self.streamInfo["Artist"])
                self.txtAlbum.set_text(self.streamInfo["Album"])
                self.txtAlbum.set_tooltip_text(self.streamInfo["Album"])
                self.txtGenre.set_text(self.streamInfo["Genre"])
                self.txtGenre.set_tooltip_text(self.streamInfo["Genre"])
                self.lblBitRate.set_label("{:3.1f} kbps".format(self.streamInfo["Bitrate"]))
                self.lblBitRate2.set_label("{:3.1f} kbps".format(self.streamInfo["Bitrate"]))
                #self.lblError.set_label("{:2.2f}% BER ".format(self.streamInfo["BER"][1]*100))
                self.lblError.set_label("{:2.2f}% BER ".format(self.streamInfo["BER"][0]*100))
                self.lblCall.set_label(" " + self.streamInfo["Callsign"])
                self.lblName.set_label(self.streamInfo["Callsign"])
                self.lblSlogan.set_label(self.streamInfo["Slogan"])
                self.lblSlogan.set_tooltip_text(self.streamInfo["Slogan"])
                self.lblMessage.set_label(self.streamInfo["Message"])
                self.lblMessage.set_tooltip_text(self.streamInfo["Message"])
                self.lblAlert.set_label(self.streamInfo["Alert"])
                self.lblAlert.set_tooltip_text(self.streamInfo["Alert"])
                self.set_button_name(self.btnAudioPrgs0,self.btnAudioLbl0,0)
                self.set_button_name(self.btnAudioPrgs1,self.btnAudioLbl1,1)
                self.set_button_name(self.btnAudioPrgs2,self.btnAudioLbl2,2)
                self.set_button_name(self.btnAudioPrgs3,self.btnAudioLbl3,3)
                self.set_label_name(self.lblAudioPrgs0, self.streamInfo["Streams"][0], True)
                self.set_label_name(self.lblAudioPrgs1, self.streamInfo["Streams"][1], True)
                self.set_label_name(self.lblAudioPrgs2, self.streamInfo["Streams"][2], True)
                self.set_label_name(self.lblAudioPrgs3, self.streamInfo["Streams"][3], True)
                self.set_label_name(self.lblAudioSvcs0, self.streamInfo["Programs"][0], True)
                self.set_label_name(self.lblAudioSvcs1, self.streamInfo["Programs"][1], True)
                self.set_label_name(self.lblAudioSvcs2, self.streamInfo["Programs"][2], True)
                self.set_label_name(self.lblAudioSvcs3, self.streamInfo["Programs"][3], True)
                self.set_label_name(self.lblDataSvcs0, self.streamInfo["Services"][0], False)
                self.set_label_name(self.lblDataSvcs1, self.streamInfo["Services"][1], False)
                self.set_label_name(self.lblDataSvcs2, self.streamInfo["Services"][2], False)
                self.set_label_name(self.lblDataSvcs3, self.streamInfo["Services"][3], False)
                self.set_label_name(self.lblDataType0, self.streamInfo["SvcTypes"][0], False)
                self.set_label_name(self.lblDataType1, self.streamInfo["SvcTypes"][1], False)
                self.set_label_name(self.lblDataType2, self.streamInfo["SvcTypes"][2], False)
                self.set_label_name(self.lblDataType3, self.streamInfo["SvcTypes"][3], False)
                self.lblMerLower.set_label("{:1.2f} dB".format(self.streamInfo["MER"][0]))
                self.lblMerUpper.set_label("{:1.2f} dB".format(self.streamInfo["MER"][1]))
                self.lblBerNow.set_label("{:1.3f}% (Now)".format(ber[0]))
                self.lblBerAvg.set_label("{:1.3f}% (Avg)".format(ber[1]))
                self.lblBerMin.set_label("{:1.3f}% (Min)".format(ber[2]))
                self.lblBerMax.set_label("{:1.3f}% (Max)".format(ber[3]))

                if (self.cbAutoGain.get_active()):
                    self.spinGain.set_value(self.streamInfo["Gain"])
                    self.lblGain.set_label("{:2.1f}dB".format(self.streamInfo["Gain"]))
                
                # second param is lot id, if -1, show cover, otherwise show cover
                # technically we should show the file with the matching lot id

                #if (int(self.lastXHDR[1]) > 0 and self.streamInfo["Cover"] != None):
                if self.lastXHDR == "0":
                    imagePath = os.path.join(aasDir, self.streamInfo["Cover"])
                    image = self.streamInfo["Cover"]
                #elif (int(self.lastXHDR[1]) < 0 or self.streamInfo["Cover"] == None):
                elif self.lastXHDR == "1":
                    imagePath = os.path.join(aasDir, self.streamInfo["Logo"])
                    image = self.streamInfo["Logo"]
                    if (not os.path.isfile(imagePath)):
                        self.imgCover.clear()
                        self.coverImage = ""
                    
                # resize and display image if it changed and exists
                #if (self.xhdrChanged and self.lastImage != image and os.path.isfile(imagePath)):
                if (self.lastImage != image) and os.path.isfile(imagePath):
                    self.xhdrChanged = False
                    self.lastImage = image
                    #img_size = min(self.alignmentCover.get_allocated_height(), self.alignmentCover.get_allocated_width()) - 12
                    #self.pixbuf = Gtk.gdk.pixbuf_new_from_file(imagePath)
                    #self.pixbuf = GdkPixbuf.Pixbuf.new_from_file(imagePath)
                    self.coverImage = imagePath
                    #self.pixbuf = self.pixbuf.scale_simple(img_size, img_size, GdkPixbuf.InterpType.BILINEAR)
                    #self.imgCover.set_from_pixbuf(self.pixbuf)
                    self.showArtwork(imagePath)
                    #self.handle_window_resize()
                    self.debugLog("Image Changed")

                if (self.cbCovers.get_active() and self.id3Changed):
                    self.get_cover_image_online()

            finally:
                #Gdk.threads_leave()
                pass        
        
        if (self.playing):
            #gobject.idle_add(update)
            GLib.idle_add(update)
            self.statusTimer = Timer(1, self.checkStatus)
            self.statusTimer.start()
    
    def processTrafficMap(self, fileName):
        global aasDir, mapDir
        r = re.compile("^[\d]+_TMT_.*_([1-3])_([1-3])_([\d]{4})([\d]{2})([\d]{2})_([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})_([0-9A-Fa-f]{4})\..*$")     # match file name
        m = r.match(fileName)
        
        if (m):
            x       = int(m.group(1))-1 # X position
            y       = int(m.group(2))-1 # Y position
            
            # get time from map tile and convert to local time
            dt = datetime.datetime(int(m.group(3)), int(m.group(4)), int(m.group(5)), int(m.group(6)), int(m.group(7)), tzinfo=tz.tzutc())
            t  = dt.astimezone(tz.tzlocal())                                                            # local time
            ts = dtToTs(dt)                                                                             # unix timestamp (utc)
            
            # check if the tile has already been loaded
            if (self.mapData["mapTiles"][x][y] == ts):
                try:
                    os.remove(os.path.join(aasDir, fileName))                                            # delete this tile, it's not needed
                except:
                    pass
                return                                                                                  # no need to recreate the map if it hasn't changed
            
            self.debugLog("Got Traffic Map Tile: {:g},{:g}".format(x,y))
                
            self.mapData["mapComplete"]    = False                                                      # new tiles are coming in, the map is nolonger complete
            self.mapData["mapTiles"][x][y] = ts                                                         # store time for current tile
            
            try:
                currentPath = os.path.join(aasDir,fileName)
                newPath = os.path.join(mapDir, "TrafficMap_{:g}_{:g}.png".format(x,y))                   # create path to new tile location
                if(os.path.exists(newPath)): os.remove(newPath)                                         # delete old image if it exists (only necessary on windows)
                shutil.move(currentPath, newPath)                                                       # move and rename map tile
            except:
                self.debugLog("Error moving map tile (src: "+currentPath+", dest: "+newPath+")", True)
                self.mapData["mapTiles"][x][y] = 0
                
            # check if all of the tiles are loaded
            if (self.checkTiles(ts)):
                self.debugLog("Got complete traffic map")
                self.mapData["mapComplete"] = True                                                      # map is complete
                
                # stitch the map tiles into one image
                imgMap = Image.new("RGB", (600, 600), "white")                                          # create blank image for traffic map
                for i in range(0,3):
                    for j in range(0,3):
                        tileFile = os.path.join(mapDir, "TrafficMap_{:g}_{:g}.png".format(i,j))          # get path to tile
                        imgMap.paste(Image.open(tileFile), (j*200, i*200))                              # paste tile into map
                        os.remove(tileFile)                                                             # delete tile image

                # now put a timestamp on it. 
                imgMap   = imgMap.convert("RGBA")
                imgBig   = (981,981)                                                                     # size of a weather map
                #posTS    = (imgMap.size[0]-235, imgMap.size[1]-29)                                      # calculate position to put timestamp (bottom right)
                posTS    = (imgBig[0]-235, imgBig[1]-29)                                                 # calculate position to put timestamp (bottom right)
                #imgTS    = self.mkTimestamp(t, imgMap.size, posTS)                                      # create timestamp
                imgTS    = self.mkTimestamp(t, imgBig, posTS)                                            # create timestamp for a weather map
                imgTS    = imgTS.resize((imgMap.size[0], imgMap.size[1]), Image.LANCZOS)                 # resize it so it's proportional to the size of a traffic map (981 -> 600)
                imgMap   = Image.alpha_composite(imgMap, imgTS)                                          # overlay timestamp on traffic map

                imgMap.save(os.path.join(mapDir, "TrafficMap.png"))                                      # save traffic map
                
                # display on map page
                if (self.radMapTraffic.get_active()):
                    img_size = min(self.alignmentMap.get_allocated_height(), self.alignmentMap.get_allocated_width()) - 12
                    #imgMap = imgMap.resize((200,200), Image.LANCZOS)                                    # scale map to fit window
                    imgMap = imgMap.resize((img_size, img_size), Image.LANCZOS)
                    self.imgMap.set_from_pixbuf(imgToPixbuf(imgMap))                                    # convert image to pixbuf and display
                
                if (self.mapViewer is not None): self.mapViewer.updated(0)                              # notify map viwerer if it's open
    
    def processWeatherOverlay(self, fileName):
        global aasDir, mapDir
        r = re.compile("^[\d]+_DWRO_(.*)_.*_([\d]{4})([\d]{2})([\d]{2})_([\d]{2})([\d]{2})_([0-9A-Fa-f]+)\..*$")                    # match file name
        m = r.match(fileName)
        
        if (m):
            # get time from map tile and convert to local time
            dt = datetime.datetime(int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)), int(m.group(6)), tzinfo=tz.tzutc())
            t  = dt.astimezone(tz.tzlocal())                                                            # local time
            ts = dtToTs(dt)                                                                             # unix timestamp (utc)
            id = self.mapData["weatherID"]
            
            if (m.group(1) != id):
                if (id == ""):
                    self.debugLog("Received weather overlay before metadata, ignoring...");
                else:
                    self.debugLog("Received weather overlay with the wrong ID: " + m.group(1) + " (wanted " + id +")")
                return
            
            if (self.mapData["weatherTime"] == ts):
                try:
                    os.remove(os.path.join(aasDir, fileName))                                            # delete this tile, it's not needed
                except:
                    pass
                return                                                                                  # no need to recreate the map if it hasn't changed
            
            self.debugLog("Got Weather Overlay")
            
            self.mapData["weatherTime"] = ts                                                            # store time for current overlay
            wxOlPath  = os.path.join(mapDir,"WeatherOverlay_{:s}_{:}.png".format(id, ts))
            wxMapPath = os.path.join(mapDir,"WeatherMap_{:s}_{:}.png".format(id, ts))
            
            # move new overlay to map directory
            try:
                if(os.path.exists(wxOlPath)): os.remove(wxOlPath)                                       # delete old image if it exists (only necessary on windows)
                shutil.move(os.path.join(aasDir, fileName), wxOlPath)                                    # move and rename map tile
            except:
                self.debugLog("Error moving weather overlay", True)
                self.mapData["weatherTime"] = 0
                
            # create weather map
            try:
                mapPath = os.path.join(mapDir, "BaseMap_" + id + ".png")                                 # get path to base map
                if (os.path.isfile(mapPath) == False):                                                  # make sure base map exists
                    self.makeBaseMap(self.mapData["weatherID"], self.mapData["weatherPos"])             # create base map if it doesn't exist
                
                imgMap   = Image.open(mapPath).convert("RGBA")                                          # open map image
                posTS    = (imgMap.size[0]-235, imgMap.size[1]-29)                                      # calculate position to put timestamp (bottom right)
                imgTS    = self.mkTimestamp(t, imgMap.size, posTS)                                      # create timestamp
                imgRadar = Image.open(wxOlPath).convert("RGBA")                                         # open radar overlay
                imgRadar = imgRadar.resize(imgMap.size, Image.LANCZOS)                                  # resize radar overlay to fit the map
                imgMap   = Image.alpha_composite(imgMap, imgRadar)                                      # overlay radar image on map
                imgMap   = Image.alpha_composite(imgMap, imgTS)                                         # overlay timestamp
                imgMap.save(wxMapPath)                                                                  # save weather map
                os.remove(wxOlPath)                                                                     # remove overlay image
                self.mapData["weatherNow"] = wxMapPath
                
                # display on map page
                if (self.radMapWeather.get_active()):
                    img_size = min(self.alignmentMap.get_allocated_height(), self.alignmentMap.get_allocated_width()) - 12
                    #imgMap = imgMap.resize((200,200), Image.LANCZOS)                                    # scale map to fit window
                    imgMap = imgMap.resize((img_size, img_size), Image.LANCZOS)                                    # scale map to fit window
                    self.imgMap.set_from_pixbuf(imgToPixbuf(imgMap))                                    # convert image to pixbuf and display
                
                self.proccessWeatherMaps()                                                              # get rid of old maps and add new ones to the list
                if (self.mapViewer is not None): self.mapViewer.updated(1)                              # notify map viwerer if it's open
                    
            except:
                self.debugLog("Error creating weather map", True)
                self.mapData["weatherTime"] = 0
            
    def proccessWeatherInfo(self, fileName):
        global aasDir
        weatherID = None
        weatherPos = None

        try:
            with open(os.path.join(aasDir, fileName)) as weatherInfo:                              # open weather info file
                for line in weatherInfo:                                                                # read line by line
                    if ("DWR_Area_ID=" in line):                                                        # look for line with "DWR_Area_ID=" in it
                        # get ID from line
                        r = re.compile("^DWR_Area_ID=\"(.+)\"$")
                        m = r.match(line)
                        weatherID = m.group(1)

                    elif ("Coordinates=" in line):                                                      # look for line with "Coordinates=" in it
                        # get coordinates from line
                        r = re.compile("^Coordinates=.*\((-?[\d]+\.[\d]+),(-?[\d]+\.[\d]+)\).*\((-?[\d]+\.[\d]+),(-?[\d]+\.[\d]+)\).*$")
                        m = r.match(line)
                        weatherPos = [float(m.group(1)),float(m.group(2)), float(m.group(3)), float(m.group(4))]
        except:
            self.debugLog("Error opening weather info", True)
        
        if (weatherID is not None and weatherPos is not None):                                          # check if ID and position were found
            if (self.mapData["weatherID"] != weatherID or self.mapData["weatherPos"] != weatherPos):    # check if ID or position has changed
                self.debugLog("Got position: ({:n}, {:n}) ({:n}, {:n})".format(*weatherPos))
                self.mapData["weatherID"]  = weatherID                                                  # set weather ID
                self.mapData["weatherPos"] = weatherPos                                                 # set weather map position
                
                self.makeBaseMap(weatherID, weatherPos)
                self.weatherMaps = []
                self.proccessWeatherMaps()
    
    def proccessWeatherMaps(self):
        global mapDir
        numberOfMaps = 0
        #r     = re.compile("^map.WeatherMap_([a-zA-Z0-9]+)_([0-9]+).png")
        r     = re.compile("^.*map.WeatherMap_([a-zA-Z0-9]+)_([0-9]+).png")
        now   = dtToTs(datetime.datetime.now(tz.tzutc()))                                               # get current time
        files = glob.glob(os.path.join(mapDir, "WeatherMap_") + "*.png")                                 # look for weather map files
        files.sort()                                                                                    # sort files
        #print(files)
        for f in files:  
            m = r.match(f)                                                                              # match regex
            if (m):
                id = m.group(1)                                                                         # location ID
                ts = int(m.group(2))                                                                    # timestamp (UTC)
                
                # remove weather maps older than 12 hours
                if (now - ts > 60*60*12):
                    try:
                        if (f in self.weatherMaps):
                            self.weatherMaps.pop(self.weatherMaps.index(f))                             # remove from list
                        os.remove(f)                                                                    # remove file
                        self.debugLog("Deleted old weather map: " + f)
                    except:
                        self.debugLog("Error Failed to Delete: " + f)
                        
                # skip if not the correct location
                elif (id == self.mapData["weatherID"]):
                    if (f not in self.weatherMaps):
                        self.weatherMaps.append(f)                          # add to list
                    numberOfMaps += 1
        

        self.debugLog("Found {} weather maps".format(numberOfMaps))
        
    def getMapArea(self, lat1, lon1, lat2, lon2):
        from math import asinh, tan, radians
        
        # get pixel coordinates from latitude and longitude
        # calculations taken from https://github.com/KYDronePilot/hdfm
        top  = asinh(tan(radians(52.482780)))
        lat1 = top - asinh(tan(radians(lat1)))
        lat2 = top - asinh(tan(radians(lat2)))
        x1   = (lon1 + 130.781250) * 7162 / 39.34135
        x2   = (lon2 + 130.781250) * 7162 / 39.34135
        y1   = lat1 * 3565 / (top - asinh(tan(radians(38.898))))
        y2   = lat2 * 3565 / (top - asinh(tan(radians(38.898))))
        
        return (int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2)))
    
    def makeBaseMap(self, id, pos):
        global mapDir
        mapPath = os.path.join(mapDir, "BaseMap_" + id + ".png")                                 # get map path
        if (os.path.isfile(self.mapFile)):
            if (os.path.isfile(mapPath) == False):                                              # check if the map has already been created for this location
                self.debugLog("Creating new map: " + mapPath)
                px     = self.getMapArea(*pos)                                                  # convert map locations to pixel coordinates        
                mapImg = Image.open(self.mapFile).crop(px)                                           # open the full map and crop it to the coordinates
                mapImg.save(mapPath)                                                            # save the cropped map to disk for later use
                self.debugLog("Finished creating map")
        else:
            self.debugLog("Error map file not found: " + self.mapFile, True)
            mapImg = Image.new("RGBA", (pos[2]-pos[1], pos[3]-pos[1]), "white")                 # if the full map is not available, use a blank image
            mapImg.save(mapPath)
    
    def checkTiles(self, t):
        # check if all the tiles have been received
        for i in range(0,3):
            for j in range(0,3):
                if (self.mapData["mapTiles"][i][j] != t):
                    return False
        return True
    
    def mkTimestamp(self, t, size, pos):
        global resDir
        # create a timestamp image to overlay on the weathermap
        x,y   = pos
        text  = "{:04g}-{:02g}-{:02g} {:02g}:{:02g}".format(t.year, t.month, t.day, t.hour, t.minute)   # format timestamp
        imgTS = Image.new("RGBA", size, (0,0,0,0))                                                      # create a blank image
        draw  = ImageDraw.Draw(imgTS)                                                                   # the drawing object
        font  = ImageFont.truetype(os.path.join(resDir,"DejaVuSansMono.ttf"), 24)                       # DejaVu Sans Mono 24pt font
        draw.rectangle((x,y, x+231,y+25), outline="black", fill=(128,128,128,96))                       # draw a box around the text
        draw.text((x+3,y), text, fill="black", font=font)                                               # draw the text
        return imgTS                                                                                    # return the image

    def parseFeedback(self, line):
        global aasDir, mapDir
        line = line.strip()
        #print(line)
        if (self.regex[4].match(line)):
            # match title
            m = self.regex[4].match(line)
            self.streamInfo["Title"] = m.group(1)
        elif (self.regex[5].match(line)):
            # match artist
            m = self.regex[5].match(line)
            self.streamInfo["Artist"] = m.group(1)
        elif (self.regex[6].match(line)):
            # match album
            m = self.regex[6].match(line)
            self.streamInfo["Album"] = m.group(1)
        elif (self.regex[15].match(line)):
            # match genre
            m = self.regex[15].match(line)
            self.streamInfo["Genre"] = m.group(1)
        elif (self.regex[3].match(line)):
            # match audio bit rate
            m = self.regex[3].match(line)
            self.streamInfo["Bitrate"] = float(m.group(1))
        elif (self.regex[8].match(line)):
            # match MER
            m = self.regex[8].match(line)
            self.streamInfo["MER"] = [float(m.group(1)), float(m.group(2))]
        elif (self.regex[9].match(line)):
            # match BER
            m = self.regex[9].match(line)
            self.streamInfo["BER"] = [float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))]
        elif (self.regex[13].match(line)):
            # match xhdr
            m = self.regex[13].match(line)
            #xhdr = [m.group(1),m.group(2)]
            xhdr = m.group(1)
            mime = m.group(2)
            lot  = m.group(3)
            if (xhdr != self.lastXHDR):
                self.lastXHDR = xhdr
                self.xhdrChanged = True
                #self.debugLog("XHDR Changed: {:s} (lot {:s})".format(xhdr[0],xhdr[1]))
                self.debugLog("XHDR Changed: {:s} (lot {:s})".format(xhdr,lot))
        elif (self.regex[7].match(line)):
            # match album art
            m = self.regex[7].match(line)
            if (m):
                fileName = "{}_{}".format(m.group(2),m.group(3))
                fileSize = int(m.group(4))
                headerOffset = int(len(m.group(2))) + 1

                p = int(m.group(1),16)

                # check file existance and size .. right now we just debug log
                if (not os.path.isfile(os.path.join(aasDir,fileName))):
                    self.debugLog("Missing file: " + fileName)
                else:
                    actualFileSize = os.path.getsize(os.path.join(aasDir,fileName))
                    if (fileSize != actualFileSize):
                        self.debugLog("Corrupt file: " + fileName + " (expected: "+fileSize+" bytes, got "+actualFileSize+" bytes)")

                #tmp = self.streams[int(self.spinStream.get_value()-1)][0]
                tmp = self.streams[int(self.streamNum)][0]

                #if (p == self.streams[int(self.spinStream.get_value()-1)][0]):
                if (p == self.streams[int(self.streamNum)][0]):
                    self.streamInfo["Cover"] = fileName
                    self.debugLog("Got Album Cover: " + fileName)
                #elif (p == self.streams[int(self.spinStream.get_value()-1)][1]):
                elif (p == self.streams[int(self.streamNum)][1]):
                    self.streamInfo["Logo"] = fileName
                    self.stationLogos[self.stationStr][self.streamNum] = fileName    # add station logo to database
                    self.debugLog("Got Station Logo: " + fileName)

                elif(fileName[headerOffset:(5+headerOffset)] == "DWRO_" and mapDir is not None):
                    self.processWeatherOverlay(fileName)
                elif(fileName[headerOffset:(4+headerOffset)] == "TMT_" and mapDir is not None):
                    self.processTrafficMap(fileName)                                  # proccess traffic map tile
                elif(fileName[headerOffset:(5+headerOffset)] == "DWRI_" and mapDir is not None):
                    self.proccessWeatherInfo(fileName)

        elif (self.regex[0].match(line)):
            # match station name
            m = self.regex[0].match(line)
            self.streamInfo["Callsign"] = m.group(1)
        elif (self.regex[2].match(line)):
            # match station slogan
            m = self.regex[2].match(line)
            self.streamInfo["Slogan"] = m.group(1)
        elif (self.regex[16].match(line)):
            # match message
            m = self.regex[16].match(line)
            self.streamInfo["Message"] = m.group(1)
        elif (self.regex[17].match(line)):
            # match alert
            m = self.regex[17].match(line)
            self.streamInfo["Alert"] = m.group(1)
        elif (self.regex[10].match(line)):
            # match gain
            m = self.regex[10].match(line)
            self.streamInfo["Gain"] = float(m.group(1))/10
        elif (self.regex[11].match(line)):
            # match stream
            m = self.regex[11].match(line)
            t = m.group(1) # stream type
            s = int(m.group(2), 10) # stream number
            n = m.group(3)

            self.debugLog("Found Stream: Type {:s}, Number {:02X}". format(t, s))
            self.lastType = t
            if (t == "audio" and s >= 1 and s <= 4):
                self.numStreams = s
                self.streamInfo["Streams"][s-1] = n
            if (t == "data"):
                self.streamInfo["Services"][self.numServices] = n
                self.numServices += 1
        elif (self.regex[12].match(line)):
            # match port and data_service_type
            m = self.regex[12].match(line)
            id = int(m.group(1), 10)
            p = int(m.group(2), 16)
            t = int(m.group(3), 10)
            self.debugLog("\tFound Port: {:03X}". format(p))
            
            if (self.lastType == "audio" and self.numStreams > 0):
                self.streams[self.numStreams-1].append(p)
            if ((self.lastType == "data") and (id == 0) and (self.numServices > 0)):
                self.streamInfo["SvcTypes"][self.numServices-1] = self.service_data_type_name(t)
        elif (self.regex[18].match(line)):
            # match program type
            m = self.regex[18].match(line)
            id = int(m.group(1), 10)
            p = int(m.group(2), 16)
            t = int(m.group(3), 10)
            
            if ((self.lastType == "audio") and (id == 0) and (self.numStreams > 0)):
                self.streamInfo["Programs"][self.numStreams-1] = self.program_type_name(t)
        elif (self.regex[19].match(line)):
            # match synchronized
            self.set_synchronization(1)
        elif (self.regex[20].match(line)):
            # match lost synch
            self.set_synchronization(0)
        elif (self.regex[21].match(line)):
            # match lost device
            self.set_synchronization(-1)
        elif (self.regex[22].match(line)):
            # match Open device failed
            self.on_btnStop_clicked(None)
            self.set_synchronization(-1)

    def getControls(self):
        global resDir
        # setup gui
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(resDir,"mainForm.glade"))
        builder.connect_signals(self)
        
        # Windows
        self.mainWindow = builder.get_object("mainWindow")
        self.mainWindow.set_icon_from_file(os.path.join(resDir,"logo.png"))
        self.mainWindow.connect("delete-event", self.shutdown)
        self.mainWindow.connect("destroy", Gtk.main_quit)
        self.about_dialog = None
        
        # get controls
        self.image1        = builder.get_object("image1")
        self.notebookMain  = builder.get_object("notebookMain")
        self.alignmentCover = builder.get_object("alignmentCover")
        self.imgCover      = builder.get_object("imgCover")
        self.alignmentMap  = builder.get_object("alignment_map")
        self.imgMap        = builder.get_object("imgMap")
        self.spinFreq      = builder.get_object("spinFreq")
        #self.spinStream    = builder.get_object("spinStream")
        self.spinGain      = builder.get_object("spinGain")
        self.spinPPM       = builder.get_object("spinPPM")
        self.spinRTL       = builder.get_object("spinRTL")
        self.cbAutoGain    = builder.get_object("cbAutoGain")
        self.cbLog         = builder.get_object("cbLog")
        self.cbCovers      = builder.get_object("cbCovers")
        self.btnPlay       = builder.get_object("btnPlay")
        self.btnStop       = builder.get_object("btnStop")
        self.btnBookmark   = builder.get_object("btnBookmark")
        self.btnDelete     = builder.get_object("btnDelete")
        self.btnMap        = builder.get_object("btnMap")
        self.radMapTraffic = builder.get_object("radMapTraffic")
        self.radMapWeather = builder.get_object("radMapWeather")
        self.txtTitle      = builder.get_object("txtTitle")
        self.txtArtist     = builder.get_object("txtArtist")
        self.txtAlbum      = builder.get_object("txtAlbum")
        self.txtGenre      = builder.get_object("txtGenre")
        self.lblName       = builder.get_object("lblName")
        self.lblSlogan     = builder.get_object("lblSlogan")
        self.lblMessage    = builder.get_object("lblMessage")
        self.lblAlert      = builder.get_object("lblAlert")
        self.btnAudioPrgs0 = builder.get_object("btn_audio_prgs0")
        self.btnAudioPrgs1 = builder.get_object("btn_audio_prgs1")
        self.btnAudioPrgs2 = builder.get_object("btn_audio_prgs2")
        self.btnAudioPrgs3 = builder.get_object("btn_audio_prgs3")
        self.btnAudioLbl0  = builder.get_object("btn_audio_lbl0")
        self.btnAudioLbl1  = builder.get_object("btn_audio_lbl1")
        self.btnAudioLbl2  = builder.get_object("btn_audio_lbl2")
        self.btnAudioLbl3  = builder.get_object("btn_audio_lbl3")
        self.lblAudioPrgs0 = builder.get_object("lbl_audio_prgs0")
        self.lblAudioPrgs1 = builder.get_object("lbl_audio_prgs1")
        self.lblAudioPrgs2 = builder.get_object("lbl_audio_prgs2")
        self.lblAudioPrgs3 = builder.get_object("lbl_audio_prgs3")
        self.lblAudioSvcs0 = builder.get_object("lbl_audio_svcs0")
        self.lblAudioSvcs1 = builder.get_object("lbl_audio_svcs1")
        self.lblAudioSvcs2 = builder.get_object("lbl_audio_svcs2")
        self.lblAudioSvcs3 = builder.get_object("lbl_audio_svcs3")
        self.lblDataSvcs0  = builder.get_object("lbl_data_svcs0")
        self.lblDataSvcs1  = builder.get_object("lbl_data_svcs1")
        self.lblDataSvcs2  = builder.get_object("lbl_data_svcs2")
        self.lblDataSvcs3  = builder.get_object("lbl_data_svcs3")
        self.lblDataType0  = builder.get_object("lbl_data_svcs10")
        self.lblDataType1  = builder.get_object("lbl_data_svcs11")
        self.lblDataType2  = builder.get_object("lbl_data_svcs12")
        self.lblDataType3  = builder.get_object("lbl_data_svcs13")
        self.lblCall       = builder.get_object("lblCall")
        self.lblGain       = builder.get_object("lblGain")
        self.lblBitRate    = builder.get_object("lblBitRate")
        self.lblBitRate2   = builder.get_object("lblBitRate2")
        self.lblError      = builder.get_object("lblError")
        self.lblMerLower   = builder.get_object("lblMerLower")
        self.lblMerUpper   = builder.get_object("lblMerUpper")
        self.lblBerNow     = builder.get_object("lblBerNow")
        self.lblBerAvg     = builder.get_object("lblBerAvg")
        self.lblBerMin     = builder.get_object("lblBerMin")
        self.lblBerMax     = builder.get_object("lblBerMax")
        self.imgNoSynch    = builder.get_object("img_nosynch")
        self.imgSynch      = builder.get_object("img_synchpilot")
        self.imgLostDevice = builder.get_object("img_lostdevice")
        self.lvBookmarks   = builder.get_object("listviewBookmarks")
        self.lsBookmarks   = Gtk.ListStore(str, str, int)
        
        self.lvBookmarks.set_model(self.lsBookmarks)
        self.lvBookmarks.get_selection().connect("changed", self.on_lvBookmarks_selection_changed)
        
        self.image1.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file(os.path.join(resDir,"weather.png")))
        self.imgNoSynch.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file(os.path.join(resDir,"nosynch.png")))
        self.imgSynch.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file(os.path.join(resDir,"synchpilot.png")))
        self.imgLostDevice.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file(os.path.join(resDir,"lostdevice.png")))
        self.btnMap.set_icon_widget(self.image1)
    
        self.mainWindow.connect("check-resize", self.on_cover_resize)

    def initStreamInfo(self):
        # stream information
        self.streamInfo = {
            "Callsign": "",         # station callsign
            "Slogan": "",           # station slogan
            "Message": "",          # station message
            "Alert": "",            # station alert
            "Title": "",            # track title
            "Album": "",            # track album
            "Genre": "",            # track genre
            "Artist": "",           # track artist
            "Cover": "",            # filename of track cover
            "Logo": "",             # station logo
            "Streams": ["","","",""],  # audio stream names
            "Programs": ["","","",""], # audio stream types
            "Services": ["","","",""], # data service names
            "SvcTypes": ["","","",""], # data service types
            "Bitrate": 0,           # current stream bit rate
            "MER": [0,0],           # modulation error ratio: lower, upper
            "BER": [0,0,0,0],       # bit error rate: current, average, min, max
            "Gain": 0               # automatic gain
        }
        
        self.streams      = [[],[],[],[]]
        self.numStreams   = 0
        self.numServices  = 0
        self.lastType     = 0
        
        # clear status info
        self.lblCall.set_label("")
        self.btnAudioLbl0.set_label("")
        self.btnAudioLbl1.set_label("")
        self.btnAudioLbl2.set_label("")
        self.btnAudioLbl3.set_label("")
        self.lblBitRate.set_label("")
        self.lblBitRate2.set_label("")
        self.lblError.set_label("")
        self.lblGain.set_label("")
        self.txtTitle.set_text("")
        self.txtArtist.set_text("")
        self.txtAlbum.set_text("")
        self.txtGenre.set_text("")
        self.imgCover.clear()
        self.coverImage = ""
        self.lblName.set_label("")
        self.lblSlogan.set_label("")
        self.lblSlogan.set_tooltip_text("")
        self.lblMessage.set_label("")
        self.lblMessage.set_tooltip_text("")
        self.btnAudioPrgs0.set_sensitive(False)
        self.btnAudioPrgs1.set_sensitive(False)
        self.btnAudioPrgs2.set_sensitive(False)
        self.btnAudioPrgs3.set_sensitive(False)
        self.lblAudioPrgs0.set_label("")
        self.lblAudioPrgs0.set_sensitive(False)
        self.lblAudioPrgs1.set_label("")
        self.lblAudioPrgs1.set_sensitive(False)
        self.lblAudioPrgs2.set_label("")
        self.lblAudioPrgs2.set_sensitive(False)
        self.lblAudioPrgs3.set_label("")
        self.lblAudioPrgs3.set_sensitive(False)
        self.lblAudioSvcs0.set_label("")
        self.lblAudioSvcs0.set_sensitive(False)
        self.lblAudioSvcs1.set_label("")
        self.lblAudioSvcs1.set_sensitive(False)
        self.lblAudioSvcs2.set_label("")
        self.lblAudioSvcs2.set_sensitive(False)
        self.lblAudioSvcs3.set_label("")
        self.lblAudioSvcs3.set_sensitive(False)
        self.lblDataSvcs0.set_label("")
        self.lblDataSvcs1.set_label("")
        self.lblDataSvcs2.set_label("")
        self.lblDataSvcs3.set_label("")
        self.lblDataType0.set_label("")
        self.lblDataType1.set_label("")
        self.lblDataType2.set_label("")
        self.lblDataType3.set_label("")
        self.lblMerLower.set_label("")
        self.lblMerUpper.set_label("")
        self.lblBerNow.set_label("")
        self.lblBerAvg.set_label("")
        self.lblBerMin.set_label("")
        self.lblBerMax.set_label("")
        self.set_synchronization(0)
    
    def loadSettings(self):
        global aasDir, cfgDir, mapDir

        # load station logos
        try:
            with open(os.path.join(cfgDir,"stationLogos.json"), mode='r') as f:
                self.stationLogos = json.load(f)
        except:
            self.debugLog("Error: Unable to load station logo database", True)

        self.mainWindow.resize(self.defaultSize[0],self.defaultSize[1])

        # load settings
        try:
            with open(os.path.join(cfgDir,"config.json"), mode='r') as f:
                config = json.load(f)
                
                if "MapData" in config:
                    self.mapData = config["MapData"]
                    if   (self.mapData["mapMode"] == 0):
                        self.radMapTraffic.set_active(True)
                        self.radMapTraffic.toggled()
                    elif (self.mapData["mapMode"] == 1):
                        self.radMapWeather.set_active(True)
                        self.radMapWeather.toggled()
                
                if "Width" and "Height" in config:
                    self.mainWindow.resize(config["Width"],config["Height"])
                else:
                    self.mainWindow.resize(self.defaultSize)

                self.mainWindow.move(config["WindowX"], config["WindowY"])
                self.spinFreq.set_value(config["Frequency"])
                #self.spinStream.set_value(config["Stream"])
                self.streamNum = config["Stream"]-1
                if (self.streamNum < 0):
                    self.streamNum = 0
                self.set_program_btns()
                self.spinGain.set_value(config["Gain"])
                self.cbAutoGain.set_active(config["AutoGain"])
                self.spinPPM.set_value(config["PPMError"])
                self.spinRTL.set_value(config["RTL"])
                self.cbLog.set_active(config["LogToFile"])
                if ("DLoadArt" in config):
                    self.cbCovers.set_active(config["DLoadArt"])
                self.bookmarks = config["Bookmarks"]
                for bookmark in self.bookmarks:
                    self.lsBookmarks.append(bookmark)
        except:
            self.debugLog("Error: Unable to load config", True)
        
        # create aas directory
        if (not os.path.isdir(aasDir)):
            try:
                os.mkdir(aasDir)
            except:
                self.debugLog("Error: Unable to create AAS directory", True)
                aasDir = None
        
        # create map directory
        if (not os.path.isdir(mapDir)):
            try:
                os.mkdir(mapDir)
            except:
                self.debugLog("Error: Unable to create Map directory", True)
                mapDir = None
        
        # open log file
        try:
            self.logFile = open("nrsc5.log", mode='a')
        except:
            self.debugLog("Error: Unable to create log file", True) 
    
    def shutdown(self, *args):
        global cfgDir
        # stop map viewer animation if it's running
        if (self.mapViewer is not None and self.mapViewer.animateTimer is not None):
            self.mapViewer.animateTimer.cancel()
            self.mapViewer.animateStop = True
            
            while (self.mapViewer.animateBusy):
                self.debugLog("Animation Busy - Stopping")
                if (self.mapViewer.animateTimer is not None):
                    self.mapViewer.animateTimer.cancel()
                time.sleep(0.25)
        
        self.playing = False
        
        # kill nrsc5 if it's running
        if (self.nrsc5 is not None and not self.nrsc5.poll()):
            self.nrsc5.kill()
        
        # shut down status timer if it's running
        if (self.statusTimer is not None):
            self.statusTimer.cancel()
        
        # wait for player thread to exit
        #if (self.playerThread is not None and self.playerThread.isAlive()):
        if (self.playerThread is not None and self.playerThread.is_alive()):
            self.playerThread.join(1)
        
        # close log file if it's enabled
        if (self.logFile is not None):
            self.logFile.close()
        
        # save settings
        try:
            with open(os.path.join(cfgDir,"config.json"), mode='w') as f:
                winX, winY = self.mainWindow.get_position()
                width, height = self.mainWindow.get_size()
                config = {
                    "CfgVersion": "1.1.0",
                    "WindowX"   : winX,
                    "WindowY"   : winY,
                    "Width"     : width,
                    "Height"    : height,
                    "Frequency" : self.spinFreq.get_value(),
                    #"Stream"    : int(self.spinStream.get_value()),
                    "Stream"    : int(self.streamNum)+1,
                    "Gain"      : self.spinGain.get_value(),
                    "AutoGain"  : self.cbAutoGain.get_active(),
                    "PPMError"  : int(self.spinPPM.get_value()),
                    "RTL"       : int(self.spinRTL.get_value()),
                    "LogToFile" : self.cbLog.get_active(),
                    "DLoadArt"  : self.cbCovers.get_active(),
                    "Bookmarks" : self.bookmarks,
                    "MapData"   : self.mapData,
                }
                # sort bookmarks
                config["Bookmarks"].sort(key=lambda t: t[2])
                
                json.dump(config, f, indent=2)
            
            with open(os.path.join(cfgDir,"stationLogos.json"), mode='w') as f:
                json.dump(self.stationLogos, f, indent=2)
        except:
            self.debugLog("Error: Unable to save config", True)
    
    def debugLog(self, message, force=False):
        if (debugMessages or force):
            now = datetime.datetime.now()
            print (now.strftime("%b %d %H:%M:%S : ") + message)

class NRSC5_Map(object):
    def __init__(self, parent, callback, data):
        global resDir
        # setup gui
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(resDir,"mapForm.glade"))
        builder.connect_signals(self)
        
        self.parent         = parent                                                # parent class
        self.callback       = callback                                              # callback function
        self.data           = data                                                  # map data
        self.animateTimer   = None                                                  # timer used to animate weather maps
        self.animateBusy    = False
        self.animateStop    = False
        self.weatherMaps    = parent.weatherMaps                                    # list of weather maps sorted by time 
        self.mapIndex       = 0                                                     # the index of the next weather map to display
        
        # get the controls
        self.mapWindow      = builder.get_object("mapWindow")
        self.imgMap         = builder.get_object("imgMap")
        self.radMapWeather  = builder.get_object("radMapWeather")
        self.radMapTraffic  = builder.get_object("radMapTraffic")
        self.chkAnimate     = builder.get_object("chkAnimate")
        self.chkScale       = builder.get_object("chkScale")
        self.spnSpeed       = builder.get_object("spnSpeed")
        self.adjSpeed       = builder.get_object("adjSpeed")
        self.imgKey         = builder.get_object("imgKey")

        self.imgKey.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file(os.path.join(resDir,"radar_key.png")))
        self.mapWindow.connect("delete-event", self.on_mapWindow_delete)
        
        self.config = data["viewerConfig"]                                          # get the map viewer config
        self.mapWindow.resize(*self.config["windowSize"])                           # set the window size
        self.mapWindow.move(*self.config["windowPos"])                              # set the window position
        if (self.config["mode"] == 0):
            self.radMapTraffic.set_active(True)        # set the map radio buttons
        elif (self.config["mode"] == 1):
            self.radMapWeather.set_active(True)
        self.setMap(self.config["mode"])                                            # display the current map
        
        self.chkAnimate.set_active(self.config["animate"])                          # set the animation mode
        self.chkScale.set_active(self.config["scale"])                              # set the scale mode
        self.spnSpeed.set_value(self.config["animationSpeed"])                      # set the animation speed
    
    def on_radMap_toggled(self, btn):
        if (btn.get_active()):
            if (btn == self.radMapTraffic):
                self.config["mode"] = 0
                self.imgKey.set_visible(False)                                                          # hide the key for the weather radar
                
                # stop animation if it's enabled
                if (self.animateTimer is not None):
                    self.animateTimer.cancel()
                    self.animateTimer = None
                
                self.setMap(0)                                                                          # show the traffic map
                
            elif (btn == self.radMapWeather):
                self.config["mode"] = 1
                self.imgKey.set_visible(True)                                                          # show the key for the weather radar
                
                # check if animate is enabled and start animation
                if (self.config["animate"] and self.animateTimer is None):
                    self.animateTimer = Timer(0.05, self.animate)
                    self.animateTimer.start()
                    
                # no animation, just show the current map
                elif(not self.config["animate"]):
                    self.setMap(1)
    
    def on_chkAnimate_toggled(self, btn):
        self.config["animate"] = self.chkAnimate.get_active()
        
        if (self.config["animate"] and self.config["mode"] == 1):
            # start animation
            self.animateTimer = Timer(self.config["animationSpeed"], self.animate)                      # create the animation timer
            self.animateTimer.start()                                                                   # start the animation timer
        else:
            # stop animation
            if (self.animateTimer is not None):
                self.animateTimer.cancel()                                                              # cancel the animation timer
                self.animateTimer = None
            self.mapIndex = len(self.weatherMaps)-1                                                     # reset the animation index
            self.setMap(self.config["mode"])                                                            # show the most recent map
    
    def on_chkScale_toggled(self, btn):
        self.config["scale"] = btn.get_active()
        if (self.config["mode"] == 1):
            if (self.config["animate"]):
                i = len(self.weatherMaps)-1 if (self.mapIndex-1 < 0) else self.mapIndex-1                 # get the index for the current map in the animation
                self.showImage(self.weatherMaps[i], self.config["scale"])                               # show the current map in the animation
            else:
                self.showImage(self.data["weatherNow"], self.config["scale"])                           # show the most recent map
    
    def on_spnSpeed_value_changed(self, spn):
        self.config["animationSpeed"] = self.adjSpeed.get_value()                                       # get the animation speed
    
    def on_mapWindow_delete(self, *args):
        # cancel the timer if it's running
        if (self.animateTimer is not None):
            self.animateTimer.cancel()
            self.animateStop = True
        
        # wait for animation to finish
        while (self.animateBusy):
            self.parent.debugLog("Waiting for animation to finish")
            if (self.animateTimer is not None):
                self.animateTimer.cancel()
            time.sleep(0.25)
        
        self.config["windowPos"]  = self.mapWindow.get_position()                                       # store current window position
        self.config["windowSize"] = self.mapWindow.get_size()                                           # store current window size
        self.callback()                                                                                 # run the callback
    
    def animate(self):
        fileName = self.weatherMaps[self.mapIndex] if len(self.weatherMaps) else ""
        if (os.path.isfile(fileName)):
            self.animateBusy = True                                                                     # set busy to true
            
            if (self.config["scale"]):
                mapImg = imgToPixbuf(Image.open(fileName).resize((600,600), Image.LANCZOS))             # open weather map, resize to 600x600, and convert to pixbuf
            else:
                mapImg = imgToPixbuf(Image.open(fileName))                                              # open weather map and convert to pixbuf
         
            if (self.config["animate"] and self.config["mode"] == 1 and not self.animateStop):          # check if the viwer is set to animated weather map
                self.imgMap.set_from_pixbuf(mapImg)                                                     # display image
                self.mapIndex += 1                                                                      # incriment image index
                if (self.mapIndex >= len(self.weatherMaps)):                                            # check if this is the last image
                    self.mapIndex = 0                                                                   # reset the map index
                    self.animateTimer = Timer(2, self.animate)                                          # show the last image for a longer time
                else:
                  self.animateTimer = Timer(self.config["animationSpeed"], self.animate)                # set the timer to the normal speed
                 
                self.animateTimer.start()                                                               # start the timer
            else:
               self.animateTimer = None                                                                 # clear the timer
               
            self.animateBusy = False                                                                    # set busy to false
        else:
            self.chkAnimate.set_active(False)                                                           # stop animation if image was not found
            self.mapIndex = 0
    
    def showImage(self, fileName, scale):
        if (os.path.isfile(fileName)):
            if (scale):
                mapImg = Image.open(fileName).resize((600,600), Image.LANCZOS)                  # open and scale map to fit window
            else:
                mapImg = Image.open(fileName)                                                   # open map
            
            self.imgMap.set_from_pixbuf(imgToPixbuf(mapImg))                                            # convert image to pixbuf and display
        else:
            #self.imgMap.set_from_stock(Gtk.STOCK_MISSING_IMAGE, Gtk.ICON_SIZE_LARGE_TOOLBAR)            # display missing image if file is not found
            #self.imgMap.set_from_stock(Gtk.STOCK_MISSING_IMAGE, Gtk.IconSize.LARGE_TOOLBAR)            # display missing image if file is not found
            self.imgMap.set_from_icon_name("MISSING_IMAGE", Gtk.IconSize.DIALOG)
    
    def setMap(self, map):
        global mapDir
        if (map == 0):
            self.showImage(os.path.join(mapDir, "TrafficMap.png"), False)                    # show traffic map
        elif (map == 1):
            self.showImage(self.data["weatherNow"], self.config["scale"])                    # show weather map
    
    def updated(self, imageType):
        if   (self.config["mode"] == 0):
            self.setMap(0)
        elif (self.config["mode"] == 1):
            self.setMap(1)
            self.mapIndex = len(self.weatherMaps)-1

def dtToTs(dt):
    # convert datetime to timestamp
    return int((dt - datetime.datetime(1970, 1, 1, tzinfo=tz.tzutc())).total_seconds())

def tsToDt(ts):
    # convert timestamp to datetime
    return datetime.datetime.utcfromtimestamp(ts)

def imgToPixbuf(img):
    # convert PIL.Image to gdk.pixbuf
    #imgArr = numpy.array(img.convert("RGB"))
    #return gtk.gdk.pixbuf_new_from_array(imgArr, gtk.gdk.COLORSPACE_RGB, 8)
    data = GLib.Bytes.new(img.tobytes())
    return GdkPixbuf.Pixbuf.new_from_bytes(data, GdkPixbuf.Colorspace.RGB, 'A' in img.getbands(),
                                           8, img.width, img.height, len(img.getbands())*img.width)


if __name__ == "__main__":
    # show main window and start main thread
    nrsc5_dui = NRSC5_DUI()
    nrsc5_dui.mainWindow.show()
    if (debugMessages and debugAutoStart):
        nrsc5_dui.on_btnPlay_clicked(nrsc5_dui)

    Gtk.main()
