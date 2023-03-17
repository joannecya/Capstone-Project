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

catchment = pd.read_csv("Simulated Data/catchment_data_1576.csv", dtype={'lat': str, 'long': str})
catchment['Address'] = catchment['lat'] + "," + catchment['long']

orders = pd.read_csv("Simulated Data/order_data_1576.csv", dtype={'long': str, 'lat': str})
all_columns = orders.columns
service_cols = all_columns[all_columns.str.contains('service')]
orders = orders.iloc[0:23]
orders['Address'] = orders['lat'].str.cat(orders['long'], sep=',')

supply_df = pd.read_csv("Simulated Data/phleb_data_1576.csv", dtype={'home_lat': str, 'home_long': str})
phleb = supply_df
phleb = phleb.iloc[0:3]
phleb['Address'] = phleb['home_lat'].str.cat(phleb['home_long'], sep=',')

inverse_ratings = 5 - phleb['service_rating']

order_window = [(6 * 60, 18 * 60)] #ending depot
order_window.extend([(int(start) * 60, (int(start)+1) * 60) for start in phleb['shift_start']])
order_window.extend([(int(start) * 60, int(start+1) * 60) for start in orders['order_start']])

numPhleb = phleb.shape[0]

revenues = [1] #ending depot
revenues.extend([1 for _ in range(numPhleb)])
revenues.extend(orders['price'])

API_key = '' #INPUT YOUR OWN API KEY

#Add Catchment Area first
addresses_list = []
addresses_list.append(catchment['Address'].iloc[0])

#Phlebotomists' Starting Points first
addresses_list.extend(phleb['Address'])
#Orders' Locations
addresses_list.extend(orders['Address'])

time_matrix = create_time_matrix(addresses_list, API_key)

servicing_times = [0]
servicing_times.extend([0 for _ in range(numPhleb)])
servicing_times.extend(orders['duration'] + orders['buffer'])

#Service-Expertise Constraints
def find_applicable_exp(row):
    args = np.empty(0)
    for val in row:
        args = np.append(args, val)
    idx = [args == 1]
    service_needs = service_cols[idx[0]]

    expertiseName = "expertise_{}".format(service_needs[0].split("_")[1])
    temp = phleb.loc[(phleb[expertiseName] == 1)]

    if len(service_needs) > 1:
        for service in service_needs[1:]:
            expertiseName = "expertise_{}".format(service.split("_")[1])
            temp = temp.loc[(temp[expertiseName] == 1)]
    
    return temp.index.to_list()

orders['Acceptable Phleb Indices'] = orders[service_cols].apply(find_applicable_exp, axis=1)
expertises = [1] #ending depot
expertises.extend([1 for _ in range(numPhleb)])
expertises.extend(orders['Acceptable Phleb Indices'])

order_ids = ["NA"] #ending depot
order_ids.extend(["NA" for _ in range(numPhleb)])
order_ids.extend(orders['order_id'])
locations_metadata = zip(addresses_list, order_ids)

metadata = {'Locations': [{"Location Index": idx, "Coordinate": metadata[0], "Order Id": str(metadata[1])}for idx, metadata in enumerate(locations_metadata)]}
metadata['Phlebotomists'] = [{"Phlebotomist Index": idx, "Id": id}for idx, id in enumerate(phleb['phleb_id'])]

result = run_algorithm(time_matrix, order_window, revenues, numPhleb, servicing_times, expertises, inverse_ratings, metadata)

json_object = json.loads(result)
routes = json_object['Routes']
routes = pd.json_normalize(routes)


def convert_to_excel(df):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    df.to_excel(writer, sheet_name="scraped data")
    writer.save()
    return output.getvalue()

def get_phleb():
    return phleb

st.title('TATA 1mg Matching Algorithm API')

st.text("")
st.text("")
st.text("")
st.text("")

#st.button(label="routes", key="get_phleb")

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

st.download_button(
    label="Get Optimal Routes",
    data=convert_to_excel(routes),
    file_name="routes.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    key="routes_download",
)

#if st.session_state.get("get_phleb"):
#    get_phleb()