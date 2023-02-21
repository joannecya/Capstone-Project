from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import requests
import json
import urllib
import urllib.request        
from flask import Flask, request, render_template
from flask_restful import Resource, Api, reqparse
from marshmallow import Schema, fields
import pandas as pd
import ast
import MatchingAlgorithm
import feature_engineering

phlebos = pd.read_csv('phleb_data_3316.csv')
orders = pd.read_csv('order_data_3316.csv')

orders = pd.read_csv("orders_new.csv", parse_dates=['order_start'], dtype={'long': str, 'lat': str})
orders['Start_Hour'] = orders['order_start'].dt.hour
orders = orders.iloc[0:10][['Start_Hour', 'duration', 'price', 'lat', 'long']]
orders['Address'] = orders['lat'].str.cat(orders['long'], sep=',')

supply_df = pd.read_csv("phlebos_new.csv", parse_dates=['shift_start_hour'], dtype={'home_lat': str, 'home_long': str, 'catchment_lat': str, 'catchment_long': str})
phleb = supply_df[['shift_start_hour', 'home_lat', 'home_long']]
phleb = phleb.iloc[0:3]
phleb['Address'] = phleb['home_lat'].str.cat(phleb['home_long'], sep=',')

catchment = supply_df.iloc[0][['catchment_lat', 'catchment_long']]
catchment['Address'] = catchment['catchment_lat'] + "," + catchment['catchment_long']

order_window = [(12 * 60, 13 * 60)] #ending depot
order_window.extend([(int(start) * 60, (int(start)+1) * 60) for start in phleb['shift_start_hour']])
order_window.extend([(int(start) * 60, int(start+1) * 60) for start in orders['Start_Hour']])

numPhleb = phleb.shape[0]

revenues = [1] #ending depot
revenues.extend([1 for _ in range(numPhleb)])
revenues.extend(orders['price'])

address = [phleb['Address'].iloc[0]] + (phleb['Address'].values.tolist()) + orders['Address'].values.tolist()

matrix = feature_engineering.main(address)

###
app = Flask(__name__)
api = Api(app)

@app.route('/phlebos')
def get_phlebos():
    data = phlebos.to_dict()
    return {'data': data}, 200 

@app.route('/orders')
def get_orders():
    data = orders.to_dict()
    return {'data': data}, 200

@app.route('/routes')
def get_routes():
    routes = MatchingAlgorithm.run_algorithm(matrix, order_window, revenues, 3)
    return {'route': routes}, 200
###

if __name__ == "__main__":
    app.run(port=8000)