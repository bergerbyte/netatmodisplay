#!/usr/bin/python
# -*- coding:utf-8 -*-
# Copyright 2022 by Sebastian Berger – V1.0.1
# All rights reserved.

import sys
import os
picdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'assets')
driverdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'driver')
configFile = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.json')
weatherCodesFile = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'weatherCodes.json')
fontsFile = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'fonts.json')

if os.path.exists(driverdir):
    sys.path.append(driverdir)

import json
import array
import logging
import time
import traceback
import netatmo
import requests
import json
from datetime import datetime
import ephem
from waveshare_epd import epd7in5_V2
from PIL import Image,ImageDraw,ImageFont

class NetamoDisplay:
    config = json.load(open(configFile))
    weatherCodes = json.load(open(weatherCodesFile))
    fonts = json.load(open(fontsFile))
    netatmoData = {}
    weatherAPIData = {}
    epd = object
    image = object
    draw = object

    def __init__(self):    
        self.initNetatmo()
        self.initWeatherAPI()
       
        self.drawScreen()
    
    def initNetatmo(self): 
        livingRoom, outdoor, bedroom = {}, {}, {}
        netatmo.fetch()
        weatherStation = netatmo.WeatherStation({
                'client_id': self.config['client_id'],
                'client_secret': self.config['client_secret'],
                'username': self.config['username'],
                'password': self.config['password'],
                'device': self.config['device'] })

        weatherStation.get_data()
        basis = weatherStation.devices[0]
        modules = basis['modules']

        #setting up rooms
        if 'dashboard_data' in basis:
            livingRoom = basis['dashboard_data']

        if 'dashboard_data' in modules[0]:
            outdoor = modules[0]['dashboard_data']

        if 'dashboard_data' in modules[1]:
            bedroom = modules[1]['dashboard_data']
        
        self.netatmoData = {'livingRoom': livingRoom, 'outdoor': outdoor, 'bedroom': bedroom}

    def initWeatherAPI(self):
        #get current weather data from open-meteo.com
        weather = requests.get('https://api.open-meteo.com/v1/forecast?latitude=' + str(self.config['latitude']) + '&longitude=' + str(self.config['longitude']) + '&hourly=weathercode&daily=sunrise,sunset&current_weather=true&timezone=Europe%2FBerlin').json()
        currentWeatherCode = weather['hourly']['weathercode'][int(datetime.now().strftime("%H"))] #get current weather code by hour
        
        #get sunrises and sunsets for the next days
        sunrises = weather['daily']['sunrise']
        sunsets = weather['daily']['sunset']
        
        self.weatherAPIData = {'currentWeatherCode': currentWeatherCode, 'sunrises': sunrises, 'sunsets': sunsets}
    
    def initEpd(self):
        try:
            self.epd = epd7in5_V2.EPD()
            self.epd.init()

            self.image = Image.open(os.path.join(picdir, 'screen.jpg'))
            self.draw = ImageDraw.Draw(self.image)
        except IOError as e:
            logging.info(e)
    
    def drawScreen(self):
        self.initEpd()

        
        self.drawCurrentWeatherImage()
        self.drawSunriseAndSunset()
        self.drawOutsideModule()
        self.drawLivingroomModule()
        self.drawBedroomModule()
        self.drawCurrentDate()
        self.drawNextFullMoon()

        #draw image to epd
        self.epd.display(self.epd.getbuffer(self.image))
        self.epd.sleep()

        #exit programm
        exit()
    
    def getFont(self, type='regular', size=20):
            return ImageFont.truetype(os.path.join(picdir, self.fonts[type]), size)
        
    def getTempraturSpited(self, value):
            return str(f"{float(value):.1f}").split('.')
        
    def getMulti(self, value, offset):
            return len(self.getTempraturSpited(value)[0]) - offset

    def getNextFullMoon(self):
        return ephem.next_full_moon(datetime.now()).datetime()
    
    def drawCurrentDate(self):
        currentDay = datetime.now().strftime("%-d.")
        currentMonth = datetime.now().strftime("%B")

        self.draw.text((50, 50), currentDay, font = self.getFont('bold', 85), fill = 0)
        self.draw.text((50, 125), currentMonth[0:3] + '.', font = self.getFont('regular', 60), fill = 0)

    def drawCurrentWeatherImage(self):
        weatherImage = Image.open(os.path.join(picdir, self.weatherCodes[str(self.weatherAPIData['currentWeatherCode'])]['name'] + '.jpg'))
        self.image.paste(weatherImage, (self.weatherCodes[str(self.weatherAPIData['currentWeatherCode'])]['x'], self.weatherCodes[str(self.weatherAPIData['currentWeatherCode'])]['y']))
    
    def drawSunriseAndSunset(self):
        if self.weatherAPIData['sunrises'] and self.weatherAPIData['sunsets']:
            sunsetImage = Image.open(os.path.join(picdir, 'sunset.jpg'))
            self.image.paste(sunsetImage, (595,113))
            self.draw.text((663, 114), self.weatherAPIData['sunsets'][0][-5:], font = self.getFont('medium', 45), fill = 0)

            sunriseImage = Image.open(os.path.join(picdir, 'sunrise.jpg'))
            self.image.paste(sunriseImage, (595,47))
            self.draw.text((663, 55), self.weatherAPIData['sunrises'][0][-5:], font = self.getFont('medium', 45), fill = 0)
    
    def drawNextFullMoon(self):
        moonImage = Image.open(os.path.join(picdir, 'moon.jpg'))
        self.image.paste(moonImage, (595,167))
        self.draw.text((667, 172), self.getNextFullMoon().strftime("%d.%m."), font = self.getFont('medium', 43), fill = 0)


    def drawOutsideModule(self):
        if self.netatmoData['outdoor']:
            self.draw.text((385, 0), self.getTempraturSpited(self.netatmoData['outdoor']['Temperature'])[0], font = self.getFont('medium', 150), fill = 0)
            self.draw.text((470 + (self.getMulti(self.netatmoData['outdoor']['Temperature'], 1) * 85), 83), '.' + self.getTempraturSpited(self.netatmoData['outdoor']['Temperature'])[1], font = self.getFont('medium', 60), fill = 0)
            self.draw.text((470 + (self.getMulti(self.netatmoData['outdoor']['Temperature'], 1) * 85), 28), '°', font = self.getFont('medium', 65), fill = 0)

            self.draw.text((225, 160), 'Luftfeuchte', font = self.getFont('bold', 30), fill = 0)
            self.draw.text((225, 190), str(int(self.netatmoData['outdoor']['Humidity'])), font = self.getFont('bold', 45), fill = 0)
            self.draw.text((278, 210), '%', font = self.getFont('medium', 24), fill = 0)

            self.draw.text((415, 160), "Luftdruck", font = self.getFont('bold', 30), fill = 0)
            self.draw.text((415, 190), str(int(self.netatmoData['livingRoom']['Pressure'])), font = self.getFont('bold', 45), fill = 0)
            self.draw.text((490 + (self.getMulti(self.netatmoData['livingRoom']['Pressure'], 3) * 30), 210), 'mbar', font = self.getFont('medium', 24), fill = 0)
        else:
            self.draw.text((355, 20), 'ERROR', font = self.getFont(), fill = 0)
            self.draw.text((215, 190), 'ERROR', font = self.getFont(), fill = 0)
            self.draw.text((435, 190), 'ERROR', font = self.getFont(), fill = 0)
    
    def drawLivingroomModule(self):
        if self.netatmoData['livingRoom']:
            self.draw.text((155, 270), self.getTempraturSpited(self.netatmoData['livingRoom']['Temperature'])[0], font = self.getFont('medium', 75), fill = 0)
            self.draw.text((243, 302), '.' + self.getTempraturSpited(self.netatmoData['livingRoom']['Temperature'])[1], font = self.getFont('medium', 40), fill = 0)
            self.draw.text((243, 283), '°', font = self.getFont('medium', 40), fill = 0)

            self.draw.text((29, 400), str(self.netatmoData['livingRoom']['Humidity']), font = self.getFont('bold', 55), fill = 0)
            self.draw.text((95, 420), '%', font = self.getFont('medium', 30), fill = 0)

            self.draw.text((205, 400), str(self.netatmoData['livingRoom']['CO2']), font = self.getFont('bold', 55), fill = 0)
            self.draw.text((305 + (self.getMulti(self.netatmoData['livingRoom']['CO2'], 3) * 35), 420), 'ppm', font = self.getFont('medium', 30), fill = 0)
        else:
            self.draw.text((170, 290), 'ERROR', font = self.getFont(), fill = 0)
            self.draw.text((40, 400), 'ERROR', font = self.getFont(), fill = 0)
            self.draw.text((210, 400), 'ERROR', font = self.getFont(), fill = 0)

    def drawBedroomModule(self):
        if self.netatmoData['bedroom']:
            self.draw.text((555, 270), self.getTempraturSpited(self.netatmoData['bedroom']['Temperature'])[0], font = self.getFont('medium', 75), fill = 0)
            self.draw.text((643, 302), '.' + self.getTempraturSpited(self.netatmoData['bedroom']['Temperature'])[1], font = self.getFont('medium', 40), fill = 0) 
            self.draw.text((643, 283), '°', font = self.getFont('medium', 40), fill = 0)

            self.draw.text((427, 400), str(self.netatmoData['bedroom']['Humidity']), font = self.getFont('bold', 55), fill = 0)
            self.draw.text((491, 420), '%', font = self.getFont('medium', 30), fill = 0)

            self.draw.text((600, 400), str(self.netatmoData['bedroom']['CO2']), font = self.getFont('bold', 55), fill = 0)
            self.draw.text((697 + (self.getMulti(self.netatmoData['bedroom']['CO2'], 3) * 35), 420), 'ppm', font = self.getFont('medium', 30), fill = 0)

        else:
            self.draw.text((570, 290), 'ERROR', font = self.getFont(), fill = 0)
            self.draw.text((430, 400), 'ERROR', font = self.getFont(), fill = 0)
            self.draw.text((600, 400), 'ERROR', font = self.getFont(), fill = 0)
        
NetamoDisplay()