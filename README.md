NRSC5-DUI is a graphical interface for [nrsc5](https://github.com/theori-io/nrsc5). It makes it easy to play your favorite FM HD radio stations using an RTL-SDR dongle. It will also display weather radar and traffic maps found on most iHeart radio stations.

This version is really a fork of a fork of the original nrsc5-gui: The first was developed by [cmnybo](https://github.com/cmnybo/nrsc5-gui) and subsequently modified by [zefie](https://github.com/zefie/nrsc5-gui). It merges the features of the former to the architecture of the latter, while adding several additional control and display features.

As such, we have changed the name to 'DUI' as a play on the Italian word for 'two', this being a second generation graphical user interface for nrsc5. (I'll be here all week. Please tip your waitresses.)

# Dependencies

The folowing programs are required to run NRSC5-DUI

* [Python 3](https://www.python.org/downloads/release)
* [PyGObject](https://pygobject.readthedocs.io/en/latest/)
* [Pillow](https://pillow.readthedocs.io/en/stable/)
* [NumPy](http://www.numpy.org)
* [Python Dateutil](https://pypi.org/project/python-dateutil)
* [urllib3](https://pypi.org/project/urllib3)
* [pyOpenSSL](https://pypi.org/project/pyOpenSSL)
* [musicbrainzngs](https://pypi.org/project/musicbrainzngs)
* [nrsc5](https://github.com/theori-io/nrsc5)
* [sox](https://github.com/chirlu/sox)

# Setup
1. Install the latest version of Python 3.9, PyGObject, Pillow, etc.
2. Compile and install nrsc5.
3. Install sox
4. Install nrsc5-dui files in a directory where you have write permissions.

The configuration and resource directories will be created in a new `cfg` and `res` directory under where nrsc5-dui.py resides. Similarly, an `aas` directory will be created for downloaded files and a `map` directory will be created to store weather & traffic maps.

nrsc5 should be installed in a directory that is in your `$PATH` environment variable. Otherwise add the full path to nrsc5 (e.g., `/usr/local/bin/`) may be entered at runtime.

# Usage
Please ensure your RTL-SDR dongle is first connected to an available USB port. Then, from the terminal, start nrsc5-dui by entering:
`python3 nrsc5-dui.py`
or something like:
`python3 nrsc5-dui.py /usr/local/bin/`
to include the path to nrsc5 when using scripts (like Apple Script) that seemingly ignore the environment.

## Settings
You may first change some optional parameters of how nrsc5 works from the Settings tab in nrsc5-dui:
Set the gain to Auto, or optionally enter an RF gain in dB that has known to work well for some stations.  
Enter a PPM correction value if your RTL-SDR dongle has an offset.  
Enter the IP address that rtl_tcp is listening to and check the Enabled box if you are using a remote RTL-SDR.  
Enter the number of the desired device if you have more than one RTL-SDR dongle.  
Check `Log to file` to enable writing debug information from nrsc5 to nrsc5.log.  
Check `DL Album Art` to enable automated downloading of album art from MusicBrainz.

## Playing
Enter the frequency in MHz of the station you want to play and either click the triangular Play button on the toolbar, or just hit return. When the receiver attains synchronization, the pilot in the lower left corner of the status bar will turn green. It will return to gray if synchronization is lost. If the device itself becomes 'lost', the pilot will turn red to indicate an error has occurred (this is the theory, though I've yet to see this status message happen in practice). The synchronization process may take about 10 seconds, and the station will begin to play. This depends upon signal strength and whether it's relatively free from adjacent interference. After a short while, the station name will appear to the right of the frequency, and the available streams will show on a row of buttons just beneath the frequency entry. Clicking one of these buttons will change to that particular stream. Note: No settings other than stream may be changed while the device is playing. 

## Album Art & Track Info
Some stations will send album art and station logos. These will fill the Album Art tab, as they are made available by the station. Most stations will send the song title, artist, album, and genre. These are displayed in the Track Info pane, also if available.
The user can override what the stations send by enabling the DL Album Art setting. This will use the Title and Artist information to retrieve album art from MusicBrainz. If no album art is found, the station logo will be used, if available.

## Bookmarks
When a station is playing, you can click the Bookmark Station button to add it to the bookmarks list. You can click on the Name in the bookmarks list to edit it. Double click the Station to tune to that particular station and stream. Click the Delete Bookmark button to delete it. Note that some stations use the default MPS/SPS or HDn naming for their streams. In this case, the bookmark will be used to name the stream button.

## Station Info
The station name, slogan, message, and optional alert message will display if the station as pre-programmed them. The current audio bit rate will be displayed here as well as on the status bar. The stations available streams and data services, with a description of each will display, as the station has pre-programmed them. This is a useful feature for noting which stations have [Total Traffic & Weather Network](https://www.ttwnetwork.com/) traffic and weather images.

### Signal Strength
The Modulation Error Ratio for the lower and upper sidebands are displayed as they are determined. Important: High MER values for both sidebands indicates a strong signal. The current, average, minimum and maximum Bit Error Rates will also be displayed as they are determined. High BER values will cause the audio to glitch or drop out. The current BER is also shown on the status bar and may be used as a tuning tool.

## Maps
When listening to radio stations operated by [iHeartMedia](http://iheartmedia.com/iheartmedia/stations), you may view live traffic maps and weather radar. The images are typically sent every few minutes and will fill the tab area once received, processed, and loaded. Clicking the Map Viewer button on the toolbar will open a larger window to view the maps at full size. The weather radar information from the last 12 hours will be stored and can be played back by selecting the Animate Radar option. The delay between frames (in seconds) can be adjusted by changing the Animation Speed value. Other stations provide [Navteq/HERE](https://www.here.com) navigation information... it's on the TODO 'like to have' list.

### Map Customization
The default map used for the weather radar comes from [OpenStreetMap](https://www.openstreetmap.org). You can replace the map.png image with a map from any website that will let you export map tiles. The tiles used are (35,84) to (81,110) at zoom level 8. The image is 12032x6912 pixels. The portion of the map used for your area is cached in the map directory. If you change the map image, you will have to delete the BaseMap images in the map directory so they will be recreated with the new map. 

## Screenshots
![album art tab](https://raw.githubusercontent.com/markjfine/nrsc5-dui/master/screenshots/Album_Art_Tab.png "Album Art Tab")
![info tab](https://raw.githubusercontent.com/markjfine/nrsc5-dui/master/screenshots/Info_Tab.png "Info Tab")
![settings tab](https://raw.githubusercontent.com/markjfine/nrsc5-dui/master/screenshots/Settings_Tab.png "Settings Tab")
![bookmarks tab](https://raw.githubusercontent.com/markjfine/nrsc5-dui/master/screenshots/Bookmarks_Tab.png "Bookmarks Tab")
![map tab](https://raw.githubusercontent.com/markjfine/nrsc5-dui/master/screenshots/Map_Tab.png "Map Tab")

## Version History
1.0.0 Initial Release  
1.0.1 Fixed compatibility with display scailing  
1.1.0 Added weather radar and traffic map viewer  
1.2.0 zefie update to modern nrsc5 build  
2.0.0 Updated to use the nrsc5 API  
2.1.0 Updated and enhanced operation and use  
