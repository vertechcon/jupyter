# -*- coding: utf-8 -*-
"""
Created: May 12, 2020
Author: Arzen Chan

Edited: May 26, 2020
"""



import pandas as pd
import geopandas
import numpy as np
import requests
import xml.etree.ElementTree as ET
import geojson
import json

import time
from datetime import datetime

pd.set_option('display.expand_frame_repr', True)

"""
Notes:
    
Geocoding errors are placed in the middle of the St. Lawrence River
45.432397, -73.532947
    
"""

def import_file_xml(xml_file_name):
    
    """Input files"""
    tree_in = ET.parse(xml_file_name) #read XML from the file
    root = tree_in.getroot()
    
    #getting categories in the XML
    #NOTE: I don't know how specific this format is to this XML file. See documentation
    columns = []
    for index, x in enumerate(root[0]):
        columns.append(root[0][index].tag)
    print ("Columns found: " + str(columns))
    
    raw_data = pd.DataFrame(columns=columns)
    
    #load data into the dataframe
    for root_index, a in enumerate(root):
        row = []
        for column_index, b in enumerate(root[root_index]):
            row.append(root[root_index][column_index].text)
        raw_data = raw_data.append(pd.Series(row, index=raw_data.columns ), ignore_index=True) #help from https://thispointer.com/python-pandas-how-to-add-rows-in-a-dataframe-using-dataframe-append-loc-iloc/
    
    #data loaded
    print (raw_data)
    
    return raw_data

def import_file_csv(csv_file_name):
    """Input files"""
    #csvFileName = input("Enter CSV File Path.\n")
    #Temporary perminant input for testing
    
    raw_data = pd.read_csv(csv_file_name, encoding="UTF-8")
    
    #data loaded
    print (raw_data)
    
    return raw_data

def to_geo_df(df):
    geo_df = geopandas.GeoDataFrame(df, geometry = geopandas.points_from_xy(df.long, df.lat))#converting to a geodataframe
    return geo_df


def geo_code(raw_data, geo_ident, geo_id_type, geo_service, geo_ident_2):
    
    """ Select 10 sample data in order to test functionality. 
    By suspending this line via making test_sample true, it will run the whole dataset"""
    
    test_sample = False #make false to run whole dataset
    if test_sample:
        raw_data = raw_data.sample(10)
    print (raw_data)
    
    
    geo_data_lat = [] #empty list to store latitude data which will be added to the dataframe
    geo_data_long = [] #empty list to store longitude data which will be added to the dataframe
    geo_data_diss = [] #empty list to store dissemination data which will be added to the dataframe
    
    if (geo_id_type == 3): #the included information is already geocoded. Just need to standardize
        geolocated_data = raw_data.rename({geo_ident: 'lat', geo_ident_2: 'long'}, axis='columns')
        
    else:
        for index, row in raw_data.iterrows():
            #the following code identifies which column is the 
            
            if (geo_service == 1 and geo_id_type == 1): #OSM, Address
                row_geo_data = get_address_data_OSM(row[geo_ident]) #call function using OSM to get the address
                
            elif (geo_service == 1 and geo_id_type == 2): #OSM, Postal Code
                print("Postal Code in OSM is not supported")
                
            elif (geo_service == 2 and geo_id_type == 1): #GCR, Address
                row_geo_data = get_address_data_GCR(row[geo_ident]) #call function using GeoCoder to get the address
            
            elif (geo_service == 2 and geo_id_type == 2): #GCR, Postal Code
                row_geo_data = get_postcode_data_GCR(row[geo_ident])
            
            #0: postal code | 1: lat | 2: long | 3: dissemination area
            geo_data_lat.append(float(row_geo_data[1]))
            geo_data_long.append(float(row_geo_data[2]))
            geo_data_diss.append(row_geo_data[3])
        
        geolocated_data = raw_data
        geolocated_data.insert(0, "lat", geo_data_lat, True) #it will insert this information at the front, standardizing the location of location information
        geolocated_data.insert(1, "long", geo_data_long, True)
        geolocated_data.insert(2, "dissemination_area", geo_data_diss, True)
    
    print (geolocated_data)
    return geolocated_data


def get_address_data_OSM(address):#using OSM Nominatim API
    """request data from nominatim"""
    
    URL = "https://nominatim.openstreetmap.org/search/"
    
    address = address.replace("Boul.", "Boulevard")
    PARAMS = {'q': address + ", Montréal",
              'format': "json"}
    
    resp = requests.get(url = URL, params = PARAMS) 
    resp = resp.text
    #print (resp)
    
    geo_data={}
    
    if resp == '[]':
        print (address +" was not found")
        geo_data[0] = address  #address saved
        geo_data[1] = 45.432397 #"Not Found"
        geo_data[2] = -73.532947 #"Not Found"
        geo_data[3] = "OSM lacks DA return" #OSM doesn't return a dissemination area. Either add that later or don't
        
        return geo_data
        
    else:
        resp_json = json.loads(resp)
        print (address + " @ " +resp_json[0]["lat"] +", "+ resp_json[0]["lon"])
    
        geo_data[0] = address  #address saved
        geo_data[1] = resp_json[0]["lat"]
        geo_data[2] = resp_json[0]["lon"]
        geo_data[3] = "OSM lacks DA return" #OSM doesn't return a dissemination area. Either add that later or don't
        
        return geo_data
    
    
def get_address_data_GCR(address):
    """request data from geocoder.ca"""
    
    address_split = address.split(maxsplit=1) #address will be split into 2 strings with the first one holding the numbers
    #note the addres MUST be in the form "1234 Street"
    num = address_split[0]
    street = address_split[1]
    
    
    URL = "https://geocoder.ca"
    
    PARAMS = {'addresst': street,
              'stno': num,
              'city': "Montreal",
              'prov':"QC",
              'geoit': "XML"}
    
    print (num + " " + street)
    
    resp = requests.get(url = URL, params = PARAMS) 
    resp = resp.content.decode()
    
    root = ET.fromstring(resp)
    
    geo_data={}
    
    geo_data[0] = address
    geo_data[1] = root[0].text #lat
    geo_data[2] = root[1].text #long
    geo_data[3] = root[3][0].text #dissemination area
    
    
    print (root[0].text)#the first child of the 'geodata' root node is the latt
    print (root[1].text)#the next child is the long
    print (root[3][0].text)#the 4th node has the dissemination area as a child
    
    return geo_data

def get_postcode_data_OSM(postal_code):#using OSM Nominatim API
    """request data from nominatim"""
    
    URL = "https://nominatim.openstreetmap.org/search/"
    
    PARAMS = {'q': postal_code,
              'format': "json"}
    
    resp = requests.get(url = URL, params = PARAMS) 
    resp = resp.text
    #print (resp)
    
    geo_data={}
    
    if resp == '[]':
        print (postal_code +" was not found")
        geo_data[0] = postal_code  #address saved
        geo_data[1] = 45.432397 #"Not Found"
        geo_data[2] = -73.532947 #"Not Found"
        geo_data[3] = "OSM lacks DA return" #OSM doesn't return a dissemination area. Either add that later or don't
        
        return geo_data
        
    else:
        resp_json = json.loads(resp)
        print (postal_code + " @ " +resp_json[0]["lat"] +", "+ resp_json[0]["lon"])
    
        geo_data[0] = postal_code  #address saved
        geo_data[1] = resp_json[0]["lat"]
        geo_data[2] = resp_json[0]["lon"]
        geo_data[3] = "OSM lacks DA return" #OSM doesn't return a dissemination area. Either add that later or don't
        
        return geo_data

def get_postcode_data_GCR(postal_code):
    """request data from geocoder.ca"""
    
    URL = "https://geocoder.ca"
    
    PARAMS = {'postal': postal_code,
              'geoit': "XML"}
    
    resp = requests.get(url = URL, params = PARAMS) 
    resp = resp.content.decode()
    
    root = ET.fromstring(resp)
    
    geo_data={}
    
    geo_data[0] = postal_code  #postal code saved
    geo_data[1] = root[0].text #lat
    geo_data[2] = root[1].text #long
    geo_data[3] = root[3][0].text #dissemination area
    
    
    print (root[0].text)#the first child of the 'geodata' root node is the latt
    print (root[1].text)#the next child is the long
    print (root[3][0].text)#the 4th node has the dissemination area as a child
    
    return geo_data

def data_out(geolocated_data, output_location):
        
    geolocated_data.to_csv(output_location+".csv", encoding="UTF-8")
    #df_to_geojson(geolocated_data, columns, output_location)#converts to geojson and outputs the data. Depreciated
    geo_data = to_geo_df(geolocated_data)
    geo_data.to_file(output_location+".geojson", driver='GeoJSON', encoding="UTF-8")
    
    print ("Process Complete")

def main():
    
    root        = 'C:/Users/Arzen/OneDrive - McGill University/2020 Work/GeoCodingScripts/file_in/'
    file_name   = 'FontEau.txt'
    
    with open(root + file_name) as f:
        in_list = f.read().splitlines()
    
    #Inputs. See the commented out section below for more details on how to set these. These are read from the file. 
    file_in_name = in_list[0]
    file_in_type = int(in_list[1])
    output_file  = in_list[2]
    geo_ident    = in_list[3]
    geo_ident_2  = in_list[4]
    geo_id_type  = int(in_list[5])
    geo_service  = int(in_list[6])
    
    print (in_list)
    
    """
    FOR USER INPUT. The input functions aren't working for whatever reason'
    
    invalid_in = True    
    print('Input File: ')
    file_in_name = input()
    
    while invalid_in:
        print('A number is used to represent the file type. Currently supported are: ')
        print('1: CSV')
        print('2: XML')
        print('Please type the appropriate number of the file type.')
        print('File Type: ')
        file_in_type = int(input())
        if file_in_type > 2 or file_in_type < 1:
            invalid_in = True
        else:
            invalid_in = False
    
    print('For the output file, do not include a file extension. The script will output both a CSV and a GeoJSON')
    print('Output File: ')
    output_file = input()
    
    print('The geographic identifier type is the form that the identifier comes in. Supported are addresses and postal codes. ')
    print('Please enter it as a number.')
    print('1: Address')
    print('2: Postal Code')
    print('3: Longitude and Latitude')
    print('Geographic Identifier Type: ')
    geo_ident = input()
    
    print('The geographic identifier is the name of the column/element that identifies the location. This could be an address, postal code, etc. ')
    print('Geographic Identifier: ')
    geo_ident = input()
    #this needs to be updated for Lat and Long bc there would need to be 2 inputs. 
    
    print('The Geolocation Service is the service you wish to use to geocode the data. We support Open Street Map and GeoCoder.ca. The latter works better for postal codes')
    print('Please enter it as a number.')
    print('1: OSM')
    print('2: Geocoder.ca (suggested for postal code)')
    print('Geolocation Service: ')
    geo_service = input()
    """
    
    #file_in_name = "C:/Users/Arzen/OneDrive - McGill University/2020 Work/Food Inspection Offenders/cusersuarcherdesktopinspection-aliments-contrevenants_SHORT.xml.xml"
    #output_file = "C:/Users/Arzen/OneDrive - McGill University/2020 Work/Food Inspection Offenders/testOut"
    
    if file_in_type == 1:
        raw_data = import_file_csv(file_in_name)
    
    elif file_in_type == 2:
        raw_data = import_file_xml(file_in_name)
    
    geolocated_data = geo_code(raw_data, geo_ident, geo_id_type, geo_service, geo_ident_2)
    
    data_out(geolocated_data, output_file)

if __name__ == "__main__":
    main()