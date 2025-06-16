## Index

* How to execute
* Problem
* Objective
* Data exploration
* Data pre-processing and machine learning
* Route data generation

## How to execute

1- Create a virtual enviroment

`python3 -m venv venv `or `python -m venv venv `

2- Execute the enviroment
`.\<environment_name>\Scripts\activate`

3- Install required libraries

`pip install -r requirements`

4- Execute `data_cleaning.ipynb` file.

5- Head to `data_pre-processing.ipynb` first cell and modify the configurations. Then execute the whole file

For custom route to function must have a .env with the google maps API key and check "Route Data Generation" requirements below.otherwise IT WILL NOT FUNCTION
API = `<API KEY>`

## Problem to solve:

Given a dataset of vehicles filtered by user preferences and a route selected by the user (from the dataset or using mapsAPI function) recommend the most suitable cars for the given route.

## Objective: 
Based on a dataset filtered on user preferences and a route, recommend the most suitable cars for the route.

## Data exploration and cleaning
<br/>File: `data_cleaning.py`
<br/>Dataset info:
<br/>Dataset file: `used_cars_data.csv`
<br/>[Dataset Link](https://www.kaggle.com/datasets/ayushparwal2026/cars-dataset/data).
<br/>This dataset has 7,253 vehicles from india:
<br/>Contains specific information about the vehicles such as :
- Name, current locaition and manufacturing year.
- Usage such as kilometers driven and also the type of Fuel and its mileage.
- Engine specifications such as cylindric capacity and brake horsepower.
<br/><br/>Things to keep in mind:
- Bad formatted data.
- Does not contain labelled data.
- Contains nulls and missing data.

Objective: Data must be analized and cleaned for further processes.

## Data pre-processing and machine learning

File info: In this file the data is analized, finds outliers and treats them accordingly. Finally uses a hybrid knowledge/content-based recommendation system.
file: `data_pre-processing.ipynb `
Dataset: `clean_car_df.csv`

1- Analyze the data, find outliers and treat them.

2- Use a model to recommend the vehicles.

## Route data generation

file: `mapsAPI.py`
Requirements: Must have a google maps API key with the following access:<br/>
* Places
* Directions
* Elevation
