from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import requests
import json
import urllib
import urllib.request        
from flask import Flask, request, render_template
from flask_restful import Resource, Api, reqparse
from marshmallow import Schema, fields
import ast
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

from FeatureEngineering import create_time_matrix
from MatchingAlgorithm import run_algorithm

orders = pd.read_csv("Simulated Data/order_data_1576.csv")
phleb = pd.read_csv("Simulated Data/phleb_data_1576.csv")
catchment = pd.read_csv("Simulated Data/catchment_data_1576.csv")

orders = orders.iloc[:23]
phleb = phleb.iloc[:3]
catchment = catchment.iloc[:1]

API_key = '' #INPUT YOUR OWN API KEY

result = run_algorithm(orders, catchment, phleb, API_key)

json_object = json.loads(result)
routes = json_object['Routes']
routes = pd.json_normalize(routes)

###
app = Flask(__name__)
api = Api(app)

@app.route('/phlebos')
def get_phlebos():
    data = phleb.to_dict()
    return {'data': data}, 200 

@app.route('/orders')
def get_orders():
    data = orders.to_dict()
    return {'data': data}, 200

@app.route('/routes')
def get_routes():
    return {'route': result}, 200
###

if __name__ == "__main__":
    app.run(port=8000)