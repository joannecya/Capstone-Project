### pip install streamlit before running this file ###

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import requests
import json
import urllib
import urllib.request        
from flask import Flask, request, render_template
from flask_restful import Resource, Api, reqparse
from marshmallow import Schema, fields
import re
import xlsxwriter
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import streamlit as st
from FeatureEngineering import create_time_matrix
from MatchingAlgorithm import run_algorithm

import firebase_admin
from firebase_admin import firestore
import pyrebase

config = {
    "apiKey": "", # Firebase API key
    "authDomain": "bt4103-capstone-e15b0.firebaseapp.com",
    "projectId": "bt4103-capstone-e15b0",
    "storageBucket": "bt4103-capstone-e15b0.appspot.com",
    "messagingSenderId": "534528759196",
    "appId": "1:534528759196:web:990717960c3b7a0e02e459",
    "measurementId": "G-EN6GENJ15Y",
    "databaseURL": "https://bt4103-capstone-e15b0-default-rtdb.asia-southeast1.firebasedatabase.app/" # additional parameter: required
}

firebase = pyrebase.initialize_app(config)
db = firebase.database()

orders = pd.DataFrame.from_dict(db.child("orders").get().val())
orders = orders[['order_start','service_artTest','service_pathology','service_vaccination','duration',
                 'price','buffer','capacity_needed','long','lat','order_id','Acceptable Phleb Indices']]

catchment = pd.DataFrame.from_dict(db.child("catchment").get().val())
catchment = catchment[['long', 'lat']]

phleb = pd.DataFrame.from_dict(db.child("phlebotomists").get().val())
phleb = phleb[['shift_start', 'break_start', 'shift_end', 'expertise_artTest', 'expertise_pathology', 'expertise_vaccination',
               'capacity', 'cost', 'service_rating', 'home_long', 'home_lat', 'phleb_id']]

def convert_to_excel(df):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    df.to_excel(writer, sheet_name="scraped data")
    writer.save()
    return output.getvalue()

def get_routes_api(orders, catchment, phleb, API_key):
    result = run_algorithm(orders, catchment, phleb, API_key)
    json_object = json.loads(result)
    routes = json_object['Routes']
    routes = pd.json_normalize(routes)
    return convert_to_excel(routes)

def get_phleb():
    return phleb

st.title('TATA 1mg Matching Algorithm API')

st.text("")
st.text("")

API_key = st.text_input("Please enter your API Key", "")

st.text("")
st.text("")
st.text("")
st.text("")

st.download_button(
    label="Get Phlebotomist Data",
    data=convert_to_excel(phleb),
    file_name="phleb.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    key="phleb_download",
)

st.download_button(
    label="Get Order Data",
    data=convert_to_excel(orders),
    file_name="orders.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    key="order_download",
)

if len(API_key) != 0:
    st.download_button(
        label="Get Optimal Routes",
        data=get_routes_api(orders, catchment.iloc[:1], phleb, API_key),
        file_name="routes.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="routes_download",
    )
