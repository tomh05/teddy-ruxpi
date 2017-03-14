# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.
import time

from adapt.intent import IntentBuilder
from multi_key_dict import multi_key_dict
from os.path import dirname
import requests 
import datetime 
import random 

from mycroft.api import Api
from mycroft.messagebus.message import Message
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

__author__ = 'jdorleans'

LOG = getLogger(__name__)


class TelevisionSkill(MycroftSkill):
    def __init__(self):
        super(TelevisionSkill, self).__init__("TelevisionSkill")

    def initialize(self):
        self.__build_current_intent()

    def __build_current_intent(self):
        intent = IntentBuilder("CurrentTelevisionIntent").require(
            "TelevisionKeyword").optionally("Channel").build()
        self.register_intent(intent, self.handle_current_intent)

   
    def handle_current_intent(self, message):
        print "handle_current_intent"
        try:
            channel = self.get_channel(message)
            print "got channel"
            # Pick a random channel
            channel_bbcone = ('BBC One', 'bbc_one_london', 'london')
            channel_bbctwo = ('BBC Two', 'bbc_two_england', 'england')
         
            print "set initial"
            all_channels = [channel_bbcone, channel_bbctwo]
            selected_channel = random.choice(all_channels)

            print "set selected chan"
         
            if channel: 
                if  "one" in channel:
                    selected_channel = channel_bbcone
                elif "two" in channel:
                    selected_channel = channel_bbctwo
         
            channel_name, channel_id, channel_region = selected_channel

            print "picked a channel",channel_name
         
            # get the schedule
            current_programme = "That programme"
            next_programme = "Something Else"
            next_minutes = 0

            try:
                today = datetime.date.today()
                r = requests.get('https://ibl.api.bbci.co.uk/ibl/v1/channels/%s/schedule/%s' %(channel_id, today))
                schedule = r.json()
                current_programme, next_programme, next_minutes = self.parse_schedule(schedule)
            except Exception as e:
	        LOG.error("Error: {0}".format(e))
                data =  { channel: channel_name }
                self.speak_dialog("cannot.find.schedule", data)
                return

            data = self.__build_data(channel_name, current_programme, next_programme, next_minutes)

            self.speak_dialog("current.television", data)

        except requests.HTTPError as e:
            self.__api_error(e)
        except Exception as e:
            LOG.error("Error: {0}".format(e))


    def parse_schedule(self, schedule):
        print "parsing schedule"
        broadcasts = schedule['schedule']['elements']
     
        print "broadcasts"
        now = datetime.datetime.now()
     
        current_programme = "this programme"
        next_programme = "something else"
        next_minutes = 0
     
        next_is_next = False
     
        for broadcast in broadcasts:
            start = self.parse_date(broadcast['scheduled_start'])
            end = self.parse_date(broadcast['scheduled_end'])
     
            if next_is_next:
                next_programme = broadcast['episode']['title']
                next_minutes = int((start - now).total_seconds()/60)
                break
            elif now >= start and now <= end:
                current_programme = broadcast['episode']['title']
                next_is_next = True
        return (current_programme, next_programme, next_minutes)
     
    def parse_date(self,date_string):
        dt = None
        try:
            format_offset = '%Y-%m-%dT%H:%M:%S.%f%z'
            dt = datetime.datetime(date_string, format_offset)
        except:
            format_zulu = '%Y-%m-%dT%H:%M:%S.%fZ'
            dt = datetime.datetime.strptime(date_string, format_zulu)
            # TODO should also set the time zone to have zero offset.
            # The date parsing may stop working in daylight saving times or time zones other than gmt.
        return dt

    def get_channel(self, message):
       try:
           channel = message.data.get("Channel", None)
           if channel:
               if "one" in channel.lower():
                  return "one" 
               elif "two" in channel.lower():
                  return "two" 
               else:
                  self.speak_dialog("channel.not.recognized")
       except:
           self.speak_dialog("channel.not.found")
           raise ValueError("Channel not found")

    def __build_data(
            self, channel_name, current_programme_name, next_programme_name, next_programme_minutes ):
        data = {
            'channel_name': channel_name,
            'current_programme_name': current_programme_name,
            'next_programme_name': next_programme_name,
            'next_programme_minutes': next_programme_minutes
        }
        return data



    def stop(self):
        pass

    def __api_error(self, e):
        if e.response.status_code == 401:
            self.emitter.emit(Message("mycroft.not.paired"))


def create_skill():
    return TelevisionSkill()
