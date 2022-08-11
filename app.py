#do the duplicate stuff for adding graphs, check if graph info is duplicate and graph name is duplicate, query?
#show if a user is already created
import dash
from dash import Dash, html,dcc,dash_table,ALL,callback_context, MATCH
from flask import redirect
import pandas as pd
from pandas import read_sql_table, read_sql_query
import plotly.express as px
from dash.dependencies import Input, Output, State
import io
import sqlite3
import base64
import sqlalchemy
from sqlalchemy import Table, create_engine
from collections import OrderedDict
import dash_bootstrap_components as dbc
import pandasql as ps
from dash_extensions.enrich import Output, DashProxy, Input, MultiplexerTransform
import plotly.graph_objects as go
import dash_mantine_components as dmc
import dash_daq as daq
from sqlalchemy.sql import select
from flask_sqlalchemy import SQLAlchemy
from flask_login import login_user, logout_user, current_user, LoginManager, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import warnings
import configparser
import os
from flask import request
from sqlalchemy import update

displayFlag = 1
global df
global queryDf
global prevTable
global userTable
userName = "Guest"
global fileName
global prevQuery
global justSignedIn
justSignedIn = False
#currFile = ""
global graphFlag
graphFlag = 0

global buttonElement
buttonElement = ["SELECT All@SELECT * FROM df"]

global graphElement
graphElement = []

##Make is so that when I sign out it changes from /success back to normal

warnings.filterwarnings("ignore")
#connect to SQLite database
conn = sqlite3.connect('auth.sqlite')
engine = create_engine('sqlite:///auth.sqlite')
db = SQLAlchemy()
config = configparser.ConfigParser()
#create users class for interacting with users table
class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(15), unique=True, nullable = False)
    buttons = db.Column(db.String(1000))
    password = db.Column(db.String(80))
    graph = db.Column(db.String(1000))
Users_tbl = Table('users', Users.metadata)

#app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])
app = DashProxy(__name__, suppress_callback_exceptions=True, prevent_initial_callbacks=True, transforms=[MultiplexerTransform()], external_stylesheets=[dbc.themes.FLATLY])
# Declare server for Heroku deployment. Needed for Procfile.
server = app.server

server.config.update(
    SECRET_KEY=os.urandom(12),
    SQLALCHEMY_DATABASE_URI='sqlite:///auth.sqlite',
    SQLALCHEMY_TRACK_MODIFICATIONS=False
)
db.init_app(server)

login_manager = LoginManager()

login_manager.init_app(server)
login_manager.login_view = '/login'
class Users(UserMixin, Users):
    pass

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

create = html.Div([html.H2('Create Account', style={'margin-left':'3vh'})
        , dcc.Location(id='create_user', refresh=True)
        , dcc.Input(id="username"
            , type="text"
            , placeholder="user name"
            , maxLength =15, style={'margin-left':'4.5vh'})
        , dcc.Input(id="password"
            , type="password"
            , placeholder="password", style={'margin-left':'4.5vh'})
        , html.Button('Create User', id='submit-val', n_clicks=0, style={'margin-left':'9vh', 'margin-top':'3vh',
        'padding':'1vh', 'font-size':'20px', 'background-color': '#4682B4', 'color':'white'}),
        html.Div(id="create_check")
        , html.Div(id='container-button-basic'),
        html.Div([html.H6('Already have a user account?', style={'margin-bottom':'0vh', 'color':'black'}), 
        dcc.Link('Click here to Log In', href='/login')])
    ])#end div

@app.callback(
   [Output("modal2", "is_open"), Output('password', 'value'), Output('username', 'value'), Output('create_check', 'children')]
    , [Input('submit-val', 'n_clicks')]
    , [State('username', 'value'), State('password', 'value'), State("modal2", "is_open")])
def insert_users(n_clicks, un, pw, is_open):
    if n_clicks > 0:
        hashed_password = generate_password_hash(pw, method='sha256')
        if un != "" and pw != "":
            names = pd.read_sql_table('users', 'sqlite:///auth.sqlite')
            if un in names["username"].values:
                return is_open, pw, un, html.H6("Username is already in use.", style={"margin-left":"10px", "font-size":"15px"})
            ins = Users_tbl.insert().values(username=un, buttons="SELECT All@SELECT * FROM df", password=hashed_password, graph="")
            conn = engine.connect()
            conn.execute(ins)
            conn.close()
            return not is_open, "", "", {}
        else:
            return is_open, pw, un, {}

login =  html.Div([dcc.Location(id='url_login', refresh=False)
            , html.H2('Sign In', id='h1', style={'margin-left':'11vh'})
            , dcc.Input(placeholder='Enter your username',
                    type='text',
                    id='uname-box', style={'margin-left':'5vh'})
            , dcc.Input(placeholder='Enter your password',
                    type='password',
                    id='pwd-box', style={'margin-left':'5vh'})
            , html.Button(children='Sign In',
                    n_clicks=0,
                    type='submit',
                    id='login-button', style={'margin-left':'12vh', 'margin-top':'3vh'
                    , 'padding':'1vh', 'font-size':'20px', 'background-color': '#4682B4', 'color':'white'})
            , html.Div(children='', id='output-state'),
            html.Div([html.H6('Do not have an user account?', style={'margin-bottom':'0vh', 'color':'black'}), 
            dcc.Link('Click here to create one', href='/')])
        ]) #end div

@app.callback(
    [Output('url_login', 'pathname'), Output('welcome', 'children'), Output('sign_in', 'children'), Output("modal2", "is_open"), 
    Output('all_buttons', 'children'), Output('all_graphs', 'children')]
    , [Input('login-button', 'n_clicks')]
    , [State('uname-box', 'value'), State('pwd-box', 'value'), State("modal2", "is_open")])
def successful(n_clicks, input1, input2, is_open):
    global userName
    global userTable
    global buttonElement
    global graphElement
    global justSignedIn
    children = []
    graphChildren = [""]
    if n_clicks > 0:
        user = Users.query.filter_by(username=input1).first()
        if user:
            if check_password_hash(user.password, input2):
                login_user(user)
                userName = str(input1)
                userTable = pd.read_sql_table('users', 'sqlite:///auth.sqlite')
                userTable = userTable[userTable['username'] == userName]
                buttons = str(userTable['buttons'].iloc[0]).split(",")
                graphs = str(userTable['graph'].iloc[0]).split(";")
                justSignedIn = True
                for button in buttons:
                    if button.strip():
                        new_element = dbc.Button("{}".format(str(button).split("@")[0]), id={
                            'type': 'dynamic-button',
                            'index': "{}".format(str(button))},
                            n_clicks=0, style={'background-color':'#d6dbe0',"margin-bottom": "10px", 'font-size':'13px', 'text-align': 'left', "margin-right": "5px"}, color="light")
                        children.append(new_element)
                buttonElement = children
                for graph in graphs:
                    if graph.strip():
                        type = str(graph).split("@")[1].split("~")[1]
                        if type == "Scatter":
                            new_element = dbc.Button([html.Img(src='assets/scatter.PNG', 
                                style={'height': '10vh', 'width':'10vh', 'margin-left':'-2px'}), 
                                html.Label("{}".format(str(graph).split("@")[0]), style={'width':'10vh'})], id={
                                'type': 'dynamic-graph',
                                'index': "{}".format(str(graph))},
                                n_clicks=0, style={'margin-right':'5px','width':'12vh', 'background-color':'#d6dbe0', 'font-size':'15px', 'text-align': 'center'}
                            )
                        elif type == "Line":
                            new_element = dbc.Button([html.Img(src='https://www.iconbunny.com/icons/media/catalog/product/2/8/2888.8-frequency-graphs-icon-iconbunny.jpg', 
                                style={'height': '10vh', 'width':'10vh', 'margin-left':'-2px'}), 
                                html.Label("{}".format(str(graph).split("@")[0]), style={'width':'10vh'})], id={
                                'type': 'dynamic-graph',
                                'index': "{}".format(str(graph))},
                                n_clicks=0, style={'margin-right':'5px','width':'12vh', 'background-color':'#d6dbe0', 'font-size':'15px', 'text-align': 'center'}
                            )
                        else:
                            new_element = dbc.Button([html.Img(src='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAOEAAADhCAMAAAAJbSJIAAAAjVBMVEX///9ktfZCQkI/Pz/5+flUVFRXV1dcXFz///1es/Xp9v////n5//xVr/Sn0/z8/vvQ5vr1+fydzPVWsvvF4Phpsu52vPeq0vfz+vm02vxesvPb6/datPqk0fNnZ2f6///C4POVy++gzOmu1+xvvvqg1PGy1vB2vPh7uuxTq+3c8PbL4vHc6fDT6vTq9v6kA2RQAAADDklEQVR4nO3cgVbaMBSA4SLiUiuL2GFZRykydco23//xhmdux50GW1lC7m3/7wn6W6E3oW2SAAAAAAAAAAAAAAB2Tv8R+2hCWE1eWfUxcTJ+5UMfC8/GJ39RqBOF+lGoH4X6UagfhfpRqB+F+lGoH4X6NQpNbYxtkSV17OPurlnYQeyDfpdGYZ2sb65abGaKIpufw6zK0+XbRk+aC01SlKM2i1pPIoUUykchhfJRSKF8zbnUVGlb4HymaPp2zKWb6TR/W/mUaS5M6kUrTQtEx+cwaV0BWz1ncJC7GL1DoX4U6uco9DmvCLisuK74F63Xw84yW2fyCr8+XHtze30XOdBRaO/yuT/lvbhzaHZri7Yd4e5GeRX7o3jY+rC7ZWUppJBCCimkkEKRhWnrhml3ubzCOru/9TZ4f3u4vRc3tSWZsfbCl9pG3x1vFtaJybyJ3rfnjqHaG+N1x8BPYe9QqB+F+g2x0C4WswCi/fGa10NbPE69y6ef5RSaokw92y0xUlmF/pYWL+ajuaBCv+vDF6mkcxikcFRSSCGFFFJIYRtp10PfU1uaLgXNpUly2fZg1/tVNzeXYgqf98a6PKH3LrHq3IU2QKKNuDHsXOP7u2PoRay6vYW9QqF+jl9mTOb7i+aZnMLdsdTev2lifts4/kttlvW60Jjt+jKAczmFSeF/u3RHzlzK6olCCimkkEIKB1FoCo+3Jv4h6RfSxFTlyONDM7+JOoe2anlW/QBTUful2Xb9KYAvcgpjrsdDGOI+Td9QqB+F+jnmUmO8PYzQ4WmF4K+BcV4P/T2N0P64QvB3+Thmmu+b4uORFNXVNnCgc/LO/f+Ov0e5nP44+jkMtD7ct6oqg8+rFFJIIYUUUkjhIAuTDm/39JkYYWqzmzzID/lujz8DB7ruGJo9nR/Ndrs4/jmsQ9wRte9GqSO86XWAuxi9Q6F+FOo3tMLYRxPC68KTkzOxVp4Kx2JNPBWKNT6jkELpKKRQPgoplO8/Ciexx7GODp/aVhMdDp+8T7U4uBAAAAAAAAAAAAAAeuUXg+QS0KF/14gAAAAASUVORK5CYII=', 
                                style={'height': '10vh', 'width':'10vh', 'margin-left':'-2px'}), 
                                html.Label("{}".format(str(graph).split("@")[0]), style={'width':'10vh'})], id={
                                'type': 'dynamic-graph',
                                'index': "{}".format(str(graph))},
                                n_clicks=0, style={'margin-right':'5px','width':'12vh', 'background-color':'#d6dbe0', 'font-size':'15px', 'text-align': 'center'}
                            )
                        graphChildren.append(new_element)
                #graphElement = graphChildren
                return '/success', html.H6("Welcome, {}".format(userName)), dbc.Button("Log Out", id="logout_button", n_clicks=0, 
                    style={'text-align':'center', 'margin-left':'5vh', 'background-color': '#4682B4','padding':'10px 25px', 'font-size':'15px'}), not is_open, children, graphChildren
            else:
                pass
        else:
            pass
    else:
        pass
@app.callback(
    [Output('output-state', 'children')]
    , [Input('login-button', 'n_clicks')]
    , [State('uname-box', 'value'), State('pwd-box', 'value')])
def update_output(n_clicks, input1, input2):
    if n_clicks > 0:
        user = Users.query.filter_by(username=input1).first()
        if user:
            if check_password_hash(user.password, input2):
                return ''
            else:
                return 'Incorrect username or password'
        else:
            return 'Incorrect username or password'
    else:
        return ''

@app.callback(Output('confirm-danger', 'displayed'), 
        Input('logout_button', 'n_clicks'))
def confirm(n_clicks):
    if n_clicks > 0:
        return True
    return False

@app.callback(
    [Output('welcome', 'children'), Output('sign_in', 'children'), Output('uname-box', 'value'), Output('pwd-box', 'value'), 
    Output('all_buttons', 'children'), Output('all_graphs', 'children'),
    Output("x_dropdown", "options"), Output("y_dropdown", "options"), Output("color_dropdown", "options"),
    Output('fileName', 'children'), Output("type_dropdown", "value"),
    Output("graph_title", "value"),Output("xlabel", "value"),Output("ylabel", "value"),Output("theme_dropdown", "value"),
    Output("marker", "value"),Output('output_table', 'children'),
    Output('the_graph', 'figure'), Output('update', 'disabled'), Output('marker', 'disabled'), Output('save_graph', 'disabled')]
    , [Input('confirm-danger', 'submit_n_clicks'), State('all_buttons', 'children')])
def newFunc(submit_n_clicks, children):
    global userName
    global buttonElement
    global graphElement
    global graphFlag
    if submit_n_clicks:
        userName = "Guest"
        buttonElement = ["SELECT All@SELECT * FROM df"]
        graphFlag = 1
        return html.H6("Welcome, Guest!"), dbc.Button("Sign In", id="sign_in_button", n_clicks=0, 
            style={'text-align':'center', 'margin-left':'5vh','padding':'10px 25px', 'font-size':'15px'}), "", "", children[0], dash_table.DataTable(
        columns=[
            {'id': "temp", 'name': ""},
        ]
    ), ['Choose a File'],['Choose a File'], ['Choose a File'], "", "Scatter", "Graph", "", "", "none", 5, html.Div(), {}, True, True, True

app.title = "My Website"


app.layout = html.Div([
    dbc.Modal([
        dbc.ModalBody([
            html.Div([
            html.Div(id='page-content', className='content')
            ,  dcc.Location(id='url', refresh=False)
            ])
        ])
    ],
    id="modal2", size="sm",
            is_open=False,),
    dcc.ConfirmDialog(
        id='confirm-danger',
        message='Are you sure you want to logout?',
    ),
    dbc.Row([
            dbc.Col(html.Div(
                        id="banner",
                        className="banner",
                        children=[html.Img(src='https://freepikpsd.com/file/2019/11/graph-icon-transparent-png-images-blue-.png', id='image', n_clicks=0),
                        html.H1("Graph Dash.ly", style={'font-size':'45px'})],
                    ), width=9),
            dbc.Col(html.Div(
                        id="welcome",
                        className="banner",
                        children=[html.H6("Welcome, {}!".format(userName), id="welcome_text", style={'text-align':'center', 'margin-left':'5vh', 'padding':'10px 25px'})],
                    ), width=2),
            dbc.Col(html.Div(
                        id="sign_in",
                        className="banner",
                        children=[dbc.Button("Sign In", id="sign_in_button", n_clicks=0, style={'text-align':'center', 'margin-left':'5vh', 'padding':'10px 25px', 'font-size':'15px'})],
                    ), width=1),
]),
    dbc.Row([dbc.Col([html.Div([
     dcc.Upload(
         id='upload-data',
         children=html.Div([
             'Drag and Drop or ',
             html.A('Select Files')
          ]),
          style={
                'height': '50px',
                'lineHeight': '50px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px',
                "margin-bottom": "20px"
            },
            # Allow multiple files to be uploaded
            multiple=False
        ),
        html.Div(id='output-data-upload', style={"margin-bottom": "20px"}),
        ##dash_table.DataTable(temp.to_dict('records'), [{"name": i, "id": i} for i in temp.columns],page_action='none',style_table={'overflowX': 'auto', 'height': '800px', 'overflowY': 'auto'}),
    ]),
    dmc.Accordion([
        dmc.AccordionItem([
        html.Div([
            html.Div([
        dbc.Label(['Graph Type']),
        dcc.Dropdown(['Scatter', 'Line', 'Bar'], id='type_dropdown',
        disabled=False,
        persistence=True,
        persistence_type='session'
        ),
    ], style={"margin-bottom": "20px"}),
            html.Div([
        dbc.Label(['X-Axis']),
        dcc.Dropdown(['Choose a File'], id='x_dropdown',
        disabled=False,
        persistence=True,
        persistence_type='session'
        ),
    ], style={"margin-bottom": "20px"}),
    html.Div([
        dbc.Label(['Y-Axis']),
        dcc.Dropdown(['Choose a File'], id='y_dropdown',
        multi=True,
        disabled=False,
        persistence=True,
        persistence_type='session'
        ),
    ], style={"margin-bottom": "20px"}),
    html.Div([
        dbc.Label(['Color By']),
        dcc.Dropdown(['Choose a File'],value="None", id='color_dropdown',
        disabled=True,
        persistence=True,
        persistence_type='session'
        ),
    ],id="color_div",style={"margin-bottom": "20px"}),
        ], style={'margin-left':'-3.65vh'})
    ], label="Graph Properties"),
    dmc.AccordionItem([
        html.Div([
            html.Div([
        dbc.Label(['Graph Title']),
        dbc.Input(id="graph_title", value="Graph"),
    ], style={"margin-bottom": "20px"}),
    html.Div([
        dbc.Label(['X-Axis Label']),
        dbc.Input(id="xlabel"),
    ], style={"margin-bottom": "20px"}),
    html.Div([
        dbc.Label(['Y-Axis Label']),
        dbc.Input(id="ylabel"),
    ], style={"margin-bottom": "20px"}),
    html.Div([
        dbc.Label(['Color Theme']),
        dcc.Dropdown(['none', 'plotly', 'plotly_white', 'plotly_dark', 'ggplot2', 'seaborn', 'simple_white'], value="none", id='theme_dropdown',
        disabled=False,
        persistence=True,
        persistence_type='session'
        ),
    ], style={"margin-bottom": "20px"}),
    html.Div([
        dbc.Label(['Marker Size']),
        daq.NumericInput(
            value=5,
            min=1,
            max=30,
            id="marker",
            disabled=True
        )   
    ], id="custom_div",style={"margin-bottom": "20px"}),
    dbc.Button("Update", id="update", disabled=True, style={'background-color':'#4682B4', 'text-align':'center', 'padding':'5px 10px', 'font-size':'12px'}),
        ], style={'margin-left':'-3.65vh'})
    ], label="Customize"),
    dmc.AccordionItem([
                html.Div([
                    dbc.Label(['Query Input']),
                html.Div(),
                html.Div(id="all_buttons", children=[dbc.Button("{}".format(str(_).split("@")[0]), id={
                'type': 'dynamic-button',
                'index': "{}".format(_)},
                n_clicks=0, style={'background-color':'#d6dbe0', "margin-bottom": "10px", 'font-size':'13px', 'text-align': 'left', "margin-right": "5px"}, color="light"
                )
                for _ in buttonElement
            ]),
                html.Div(dcc.Textarea(
                id='textarea-state-example',
                placeholder='Type your own SQL query',
                style={'width': '42vh', 'height': '200px'},
                )),
                dbc.Button('Submit', id='textarea-state-example-button', n_clicks=0, style={'background-color':'#4682B4', "margin-bottom": "5px", 'margin-right': '10px'}),
                dbc.Button('Save Query', id='save_query', n_clicks=0, style={'background-color':'#4682B4', "margin-bottom": "5px"}),
                html.Div(id='textarea-state-example-output', style={'whiteSpace': 'pre-line', "margin-bottom": "20px"}),
                dbc.Modal(
                [
                    dbc.ModalHeader("Name your query"),
                    dbc.ModalBody([
                    dbc.Input(id="query_name"),
                    html.Div(id='name-output', style={'whiteSpace': 'pre-line', "margin-bottom": "20px"}),
                ]),
                    dbc.ModalFooter(
                    dbc.Button("Save", id="save", className="ml-auto")
                ),
            ],
            id="modal"),
                ], style={'margin-left':'-3.65vh'})
    ], label="SQL Analysis"),
    dmc.AccordionItem([
                html.Div([
                html.Div(id="all_graphs", children=[dbc.Button([html.Img(src='https://freepikpsd.com/file/2019/11/graph-icon-transparent-png-images-blue-.png', 
                        style={'height': '10vh', 'width':'10vh', 'margin-left':'-2px'}), 
                        html.Label("{}".format(str(_).split("@")[0]), style={'width':'10vh'})], id={
                'type': 'dynamic-graph',
                'index': "{}".format(str(_))},
                n_clicks=0, style={'margin-right':'5px', 'width':'12vh', 'background-color':'#d6dbe0', 'font-size':'15px', 'text-align': 'center'}
                )
                for _ in graphElement
            ]),
                html.Div(id='graph_output', style={'whiteSpace': 'pre-line', "margin-bottom": "20px"}),
                dbc.Modal(
                [
                    dbc.ModalHeader("Name your graph"),
                    dbc.ModalBody([
                    dbc.Input(id="graph_name"),
                    html.Div(id='graph-output', style={'whiteSpace': 'pre-line', "margin-bottom": "20px"}),
                ]),
                    dbc.ModalFooter(
                    dbc.Button("Save", id="save-graph",className="ml-auto")
                ),
            ],
            id="graph_modal"),
                ], style={'margin-left':'-3.65vh'})
    ], label="Saved Graphs"),
    ], multiple=True, state={"0": True, "1": False, "2": False},),
    ], width=3), dbc.Col([dbc.Row([dbc.Col(html.Div(html.H5("No File Selected"),id='fileName')),
    dbc.Col(dbc.Button('Save Graph', id='save_graph', n_clicks=0, disabled=True,
    style={'text-align':'center', 'background-color':'#4682B4', 'margin-top':'1vh', 'margin-left':'55.5vh','padding':'8px 17px', 'font-size':'13px'}))]),
    html.Div(dcc.Graph(id='the_graph', style={'height': '80vh'}), id="graph_div"),
    html.Div(id='output_table', children=[
        dash_table.DataTable(
        columns=[
            {'id': "temp", 'name': ""},
        ]
    )
    ], style={'margin-top':'3vh'})], width=9)]),
], style={'background-image': 'url("/assets/webbg.jpg")', 'background-repeat': 'repeat', 'padding':'20px', 'margin':'0px'})


#callback to determine layout to return
@app.callback(
    Output('page-content', 'children')
    , [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/':
        return create
    elif pathname == '/login':
        return login
    else:
        return create

def parse_contents(contents, filename, date):
    global df

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    try:
        if 'csv' in filename:
            # Assume that the user uploaded a CSV file
            df = pd.read_csv(
                io.StringIO(decoded.decode('utf-8')))
        elif 'xls' in filename:
            # Assume that the user uploaded an excel file
            df = pd.read_excel(io.BytesIO(decoded))
    except Exception as e:
        print(e)
        return html.Div([
            'There was an error processing this file.'
        ])

    global queryDf
    queryDf = df


@app.callback([Output('color_dropdown', 'options'), Output('x_dropdown', 'options'), Output('y_dropdown', 'options'), Output(component_id='output_table', component_property='children')],
            [Input('upload-data', 'contents'), State('upload-data', 'filename'), State('upload-data', 'last_modified')])

def update_output(list_of_contents, list_of_names, list_of_dates):
    global df
    global queryDf
    global prevTable
    global prevQuery
    conn = sqlite3.connect('OurData.db')
    db_uri = 'sqlite:///OurData.db'
    engine = sqlalchemy.create_engine(db_uri, echo=False)
    insp = sqlalchemy.inspect(engine)
    if(insp.has_table(list_of_names)):
        df = pd.read_sql_table(list_of_names, 'sqlite:///OurData.db')
    else:
        if list_of_contents is not None:
            #connection = sqlite3.connect('OurData.db')
            parse_contents(list_of_contents, list_of_names, list_of_dates)
            df.to_sql(list_of_names, con=conn, if_exists='append', index=False)
    queryDf = df
    prevTable = df
    prevQuery = ""
    return ["None"]+list(df.columns), list(df.columns), list(df.columns), html.Div([dash_table.DataTable(queryDf.to_dict('records'), [{"name": i, "id": i} for i in queryDf.columns],
            style_cell={
                'whiteSpace': 'normal', 'minWidth': 150, 'maxWidth': 150, 'width': 150
            }, id='my_table', style_data_conditional=[{'width':'25px'}],
            fixed_rows={'headers': True}, page_action='none', virtualization=True)])


##create new callback that ttakes the xdropdowna and ydropdown as inputs. If the len of ydropdown is 1 display the color dropdown, otherwise hide it
@app.callback(
    [Output(component_id='color_dropdown', component_property='disabled'), Output('save_graph', 'disabled')],
    [Input('type_dropdown','value'), Input(component_id='x_dropdown', component_property='value'), Input(component_id='y_dropdown', component_property='value')]
)

def hide_display(type, x_dropdown, y_dropdown):
    if str(type) == 'Line':
        return True, False
    if(len(x_dropdown) == 0):
        return True, False
    if(len(y_dropdown) == 1):
        return False, False
    else:
        return True, False
Output('update', 'disabled'), Output('marker', 'disabled')
@app.callback(
    [Output(component_id='the_graph', component_property='figure'), Output('update', 'disabled'), Output('graph_title', 'value'),
    Output('xlabel', 'value'), Output('ylabel', 'value'), Output('marker', 'value'), Output('color_dropdown', 'value'), Output('marker', 'disabled')],
    [Input(component_id='type_dropdown', component_property='value'), Input(component_id='color_dropdown', component_property='value'), 
    Input(component_id='x_dropdown', component_property='value'), Input(component_id='y_dropdown', component_property='value')],
    [State('graph_title','value'),
    State('marker', 'value'), State('theme_dropdown', 'value')]
)

def update_graph(type, color, x_dropdown, y_dropdown, title, marker, theme):
    global fig
    global graphFlag
    if graphFlag == 0:
        temp = queryDf
        y = ""
        val = color
        disabled = True
        if str(type) == 'Scatter':
            if(len(y_dropdown) == 1):
                if color == "None":
                    fig = px.scatter(temp, x=str(x_dropdown), y=str(y_dropdown[0]), title="Graph")
                else:
                    fig = px.scatter(temp, x=str(x_dropdown), y=str(y_dropdown[0]), color=str(color), title="Graph")
                fig.update_traces(marker={'size': 5})
                y = str(y_dropdown[0])
                disabled = False
            else:
                values = []
                for items in y_dropdown:
                    values.append(items)
                table = pd.pivot_table(temp, values=values, index = str(x_dropdown))

                data = []
                for items in y_dropdown:
                    trace = go.Scatter(x=table.index, y=table[(str(items))], mode='markers', name=str(items))
                    data.append(trace)

                fig = go.Figure(data=data) 

                y = ""
                for thing in y_dropdown:
                    y = y + str(thing) + " "

                val = "None"
                disabled = False

                fig.update_traces(marker={'size': 5})
                fig.update_layout(xaxis_title=x_dropdown, yaxis_title=y, title="Graph")
        elif str(type) == 'Line':
            values = []
            for items in y_dropdown:
                values.append(items)
            table = pd.pivot_table(temp, values=values, index = str(x_dropdown))

            data = []
            for items in y_dropdown:
                trace = go.Scatter(x=table.index, y=table[(str(items))], mode='lines+markers', name=str(items))
                data.append(trace)

            fig = go.Figure(data=data) 

            y = ""
            for thing in y_dropdown:
                y = y + str(thing) + " "

            val = "None"
            disabled = False

            fig.update_traces(marker={'size': 5})
            fig.update_layout(xaxis_title=x_dropdown, yaxis_title=y, title="Graph")
        else:
            if len(y_dropdown) == 1:
                if color == "None":
                    fig = px.bar(temp, x=str(x_dropdown), y=list(y_dropdown))
                else:
                    fig = px.bar(temp, x=str(x_dropdown), y=list(y_dropdown), color=str(color))
            else:
                fig = px.bar(temp, x=str(x_dropdown), y=list(y_dropdown))
                val = "None"
            y = ""
            for thing in y_dropdown:
                y = y + str(thing) + " "
            fig.update_layout(xaxis_title=x_dropdown, yaxis_title=y, title="Graph")

        fig = new_custom_graph(type, title, marker, theme)
        return (fig), False, "Graph", x_dropdown, y, 5, val, disabled
    else:
        graphFlag = 0
        dash.no_update

def new_custom_graph(type, title, marker, theme):
    global fig
    if(type == 'Bar'):
        fig.update_layout(title=title, template=theme)
    else:
        fig.update_traces(marker={'size': marker})
        fig.update_layout(title=title, template=theme)

    return (fig)

# @app.callback(Output('tbl_out', 'children'), Input('my_table', 'active_cell'))

# def display_cell(active_cell):
#     return str(active_cell) if active_cell else ""

@app.callback(Output('fileName', 'children'),
            [Input('upload-data', 'filename')])

def update_name(name):
    ##if list_of_contents is not None:
    global fileName
    fileName = str(name)
    return html.H5(str(name))

@app.callback(
    [Output(component_id='output_table', component_property='children'),Output('textarea-state-example-output', 'children'), Output('color_dropdown', 'options'), Output('x_dropdown', 'options'), Output('y_dropdown', 'options')],
    Input('textarea-state-example-button', 'n_clicks'),
    State('textarea-state-example', 'value')
)
def update_output(n_clicks, value):
    global queryDf
    global prevTable
    global prevQuery
    if n_clicks > 0:
        query = str(value).strip()
        try:
            #temp = ps.sqldf("Select * from df")
            queryDf = ps.sqldf(query)
            prevTable = queryDf
            prevQuery = query
        except:
            return html.Div([dash_table.DataTable(prevTable.to_dict('records'), [{"name": i, "id": i} for i in prevTable.columns],
            style_cell={
                'whiteSpace': 'normal', 'minWidth': 150, 'maxWidth': 150, 'width': 150
            }, id='my_table', style_data_conditional=[{'width':'25px'}],  
            fixed_rows={'headers': True}, page_action='none', virtualization=True)]),"Invalid Query",  ["None"]+list(prevTable.columns), list(prevTable.columns), list(prevTable.columns)
    #print(queryDf)
    return html.Div([dash_table.DataTable(queryDf.to_dict('records'), [{"name": i, "id": i} for i in queryDf.columns],
            style_cell={
                'whiteSpace': 'normal', 'minWidth': 150, 'maxWidth': 150, 'width': 150
            }, id='my_table', style_data_conditional=[{'width':'25px'}],
            fixed_rows={'headers': True}, page_action='none', virtualization=True)]), '{}'.format(value), ["None"]+list(queryDf.columns), list(queryDf.columns), list(queryDf.columns)


@app.callback(
    [Output('all_buttons', 'children'), Output("modal", "is_open"), Output('textarea-state-example', 'value'), Output('textarea-state-example-output', 'children'), Output('name-output', 'children')],
    [Input('save', 'n_clicks')],
    [State('query_name', 'value'), State('textarea-state-example', 'value'), State('all_buttons', 'children'), State("modal", "is_open")],
)
def add_strategy_divison(n_clicks, name, value, children, is_open):
    global buttonElement

    if n_clicks > 0:
        query = str(value).strip()

        for element in buttonElement:
            if str(element).split("@")[0].strip() == str(name).strip():
                return children, is_open, query, query, "Duplicate Name"

        query = str(name) + "@" + query
        dbquery = str(userTable['buttons'].iloc[0]) + "," + query

        try:
            sqliteConnection = sqlite3.connect('auth.sqlite')
            cursor2 = sqliteConnection.cursor()
            print("Connected to SQLite")
            sql_update_query = """UPDATE users SET buttons=? WHERE username=?"""
            data = (dbquery, userName)
            cursor2.execute(sql_update_query, data)
            sqliteConnection.commit()
            print("Record Updated successfully ")
            cursor2.close()

        except sqlite3.Error as error:
            print("Failed to update sqlite table", error)
        finally:
            if sqliteConnection:
                sqliteConnection.close()
                print("The SQLite connection is closed")

        new_element = dbc.Button("{}".format(str(query).split("@")[0]), id={
            'type': 'dynamic-button',
            'index': "{}".format(str(query))},
            n_clicks=0, style={'background-color':'#d6dbe0',"margin-bottom": "10px", 'font-size':'13px', 'text-align': 'left', "margin-right": "5px"}, color="light")

        buttonElement.append(query.strip())

        children.append(new_element)
        return children, not is_open, str(value).strip(), str(value).strip(), ""

@app.callback(
    Output('textarea-state-example', 'value'),
    Input({'type':'dynamic-button','index': ALL}, 'n_clicks'),
)
def displayClick(*n_clicks):
    trigger = callback_context.triggered[0]
    trigger = trigger["prop_id"].split(".")[0]
    trigger = trigger[:-25]
    trigger = trigger.split(":")[1]
    trigger = trigger.split("@")[1]
    return trigger[:-1].replace("\\", "").strip()


@app.callback(
    [Output("x_dropdown", "options"), Output("y_dropdown", "options"), Output("color_dropdown", "options"),
    Output('fileName', 'children'), Output("type_dropdown", "value"), Output("x_dropdown", "value"), Output("y_dropdown", "value"), Output("color_dropdown", "value"),
    Output("graph_title", "value"),Output("xlabel", "value"),Output("ylabel", "value"),Output("theme_dropdown", "value"),
    Output("marker", "value"),Output('output_table', 'children'),
    Output('the_graph', 'figure'), Output('update', 'disabled'), Output('marker', 'disabled')],
    Input({'type':'dynamic-graph','index': ALL}, 'n_clicks')
)##allow for update, make it not initially called, make it so graph updates
def displayClick(*n_clicks):
    global justSignedIn
    global graphFlag
    global fileName
    if justSignedIn == False:
        trigger = callback_context.triggered[0]
        #print(trigger)
        trigger = trigger["prop_id"].split(".")[0] + "." + trigger["prop_id"].split(".")[1]
        trigger = trigger[:-25]
        trigger = trigger.split(":")[1]
        trigger = trigger.split("@")[1]
        list = trigger.split("~")
        list[3] = list[3]
        ylist = list[3].split(",")[1:]
        #print(ylist[0])
        #print(ylist)

        table = my_update_table(list[0])

        graphStuff = my_update_graph(list[1], list[4], list[2], ylist)

        graph = my_customize_graph(list[1], list[5], list[6], list[7], int(list[9]), list[8])
        graphFlag = 1
        fileName = list[0]
        return table[1], table[2], table[0], html.H5(list[0]), list[1], list[2], ylist, list[4], list[5], list[6], list[7], list[8], int(list[9]), table[3], graph, graphStuff[1], graphStuff[2]
    else:
        #print("justSignedIN")
        justSignedIn = False
        return dash.no_update

def my_customize_graph(type, title, x, y, marker, theme):
    global fig
    if(type == 'Bar'):
        fig.update_layout(xaxis_title=x, yaxis_title=y, title=title, template=theme)
    else:
        fig.update_traces(marker={'size': marker})
        fig.update_layout(xaxis_title=x, yaxis_title=y, title=title, template=theme)

    return (fig)

def my_update_graph(type, color, x_dropdown, y_dropdown):
    global fig
    temp = queryDf
    y = ""
    val = color
    disabled = True
    if str(type) == 'Scatter':
        if(len(y_dropdown) == 1):
            if color == "None":
                fig = px.scatter(temp, x=str(x_dropdown), y=str(y_dropdown[0]), title="Graph")
            else:
                fig = px.scatter(temp, x=str(x_dropdown), y=str(y_dropdown[0]), color=str(color), title="Graph")
            fig.update_traces(marker={'size': 5})
            y = str(y_dropdown[0])
            disabled = False
        else:
            values = []
            for items in y_dropdown:
                values.append(items)
            table = pd.pivot_table(temp, values=values, index = str(x_dropdown))

            data = []
            for items in y_dropdown:
                trace = go.Scatter(x=table.index, y=table[(str(items))], mode='markers', name=str(items))
                data.append(trace)

            fig = go.Figure(data=data) 

            y = ""
            for thing in y_dropdown:
                y = y + str(thing) + " "

            val = "None"
            disabled = False

            fig.update_traces(marker={'size': 5})
            fig.update_layout(xaxis_title=x_dropdown, yaxis_title=y, title="Graph")
    elif str(type) == 'Line':
        values = []
        for items in y_dropdown:
            values.append(items)
        table = pd.pivot_table(temp, values=values, index = str(x_dropdown))

        data = []
        for items in y_dropdown:
            trace = go.Scatter(x=table.index, y=table[(str(items))], mode='lines+markers', name=str(items))
            data.append(trace)

        fig = go.Figure(data=data) 

        y = ""
        for thing in y_dropdown:
            y = y + str(thing) + " "

        val = "None"
        disabled = False

        fig.update_traces(marker={'size': 5})
        fig.update_layout(xaxis_title=x_dropdown, yaxis_title=y, title="Graph")
    else:
        if len(y_dropdown) == 1:
            if color == "None":
                fig = px.bar(temp, x=str(x_dropdown), y=list(y_dropdown))
            else:
                fig = px.bar(temp, x=str(x_dropdown), y=list(y_dropdown), color=str(color))
        else:
            fig = px.bar(temp, x=str(x_dropdown), y=list(y_dropdown))
            val = "None"
        y = ""
        for thing in y_dropdown:
            y = y + str(thing) + " "
        fig.update_layout(xaxis_title=x_dropdown, yaxis_title=y, title="Graph")

    return (fig), False, disabled

def my_update_table(name):
    global df
    global queryDf
    global prevTable
    global prevQuery
    conn = sqlite3.connect('OurData.db')
    db_uri = 'sqlite:///OurData.db'
    engine = sqlalchemy.create_engine(db_uri, echo=False)
    insp = sqlalchemy.inspect(engine)
    df = pd.read_sql_table(name, 'sqlite:///OurData.db')
    queryDf = df
    prevTable = df
    prevQuery = ""
    return ["None"]+list(df.columns), list(df.columns), list(df.columns), html.Div([dash_table.DataTable(queryDf.to_dict('records'), [{"name": i, "id": i} for i in queryDf.columns],
            style_cell={
                'whiteSpace': 'normal', 'minWidth': 150, 'maxWidth': 150, 'width': 150
            }, id='my_table', style_data_conditional=[{'width':'25px'}],
            fixed_rows={'headers': True}, page_action='none', virtualization=True)])


@app.callback(
    [Output("modal", "is_open"),  Output('textarea-state-example', 'value'), Output('textarea-state-example-output', 'children')],
    [Input("save_query", "n_clicks")],
    [State("modal", "is_open"), State('textarea-state-example', 'value')],
)
def toggle_modal(n1, is_open, value):
    global buttonElement
    if n1 > 0:
        if not userName == "Guest":
            query = str(value).strip()
            try:
                ans = ps.sqldf(query)
                for element in buttonElement:
                    if str(element).split("@")[1].strip() == query.strip():
                        return is_open, query, "Duplicate Query"
                    elif not query.strip():
                        return is_open, query, "Invalid Query"
                return not is_open, query, query
            except:
                return is_open, query, "Invalid Query"
        else:
            return is_open, value, "Sign in to save queries"
    
@app.callback(
    Output("accordion-contents", "children"),
    [Input("accordion", "active_item")],
)
def change_item(item):
    return f"Item selected: {item}"

@app.callback(
    [Output(component_id='the_graph', component_property='figure')],
    Input('update', 'n_clicks'),
    [State('type_dropdown', 'value'), State('graph_title','value'), State('xlabel','value'), State('ylabel','value'),
    State('marker', 'value'), State('theme_dropdown', 'value')]
)

def update_graph(n_clicks, type, title, x, y, marker, theme):
    global fig
    if(n_clicks > 0):
        if(type == 'Bar'):
            fig.update_layout(xaxis_title=x, yaxis_title=y, title=title, template=theme)
        else:
            fig.update_traces(marker={'size': marker})
            fig.update_layout(xaxis_title=x, yaxis_title=y, title=title, template=theme)

    return (fig)

@app.callback(
    Output("modal2", "is_open"),
    [Input("sign_in_button", "n_clicks")],
    [State("modal2", "is_open")],
)
def toggle_modal2(n1, is_open):
    if n1:
        return not is_open
    return is_open

# file, graph type, x-axis, y-axis, color by, graph title, x-axis label, yaxis label, color theme, marker size, sql query
@app.callback(
    Output("graph_modal", "is_open"),
    [Input("save_graph", "n_clicks")],
    [State("type_dropdown", "value"), State("x_dropdown", "value"), State("y_dropdown", "value"), State("graph_modal", "is_open")],
)
def save_graph_info(n_clicks, type, x, y, is_open):
    global fileName
    global userName
    print(userName)
    print(n_clicks)
    if n_clicks > 0:
        print("z")
        if not userName == "Guest":
            print("x")
            print(fileName)
            print(type)
            print(x)
            print(y)
            if not fileName or not type or not x or not y:
                print("Y")
                return is_open 
            return not is_open
            
        #do this with the sql stuff

@app.callback(
    [Output("graph_modal", "is_open"), Output("all_graphs", "children")],
    [Input("save-graph", "n_clicks")],
    [State("type_dropdown", "value"), State("x_dropdown", "value"), State("y_dropdown", "value"), State("color_dropdown", "value"),
    State("graph_title", "value"),State("xlabel", "value"),State("ylabel", "value"),State("theme_dropdown", "value"),
    State("marker", "value"), State("graph_modal", "is_open"), State("graph_name", "value"), State("all_graphs", "children")],
)
def save_graph_button(n_clicks, type, x, y, color, title, xlabel, ylabel, theme, marker, is_open, name, children):
    global userName
    global prevQuery
    global graphElement
    global userTable
    global justSignedIn
    if n_clicks > 0:
   #     for element in graphElement:
    #        if str(element).split("@")[0].strip() == str(name).strip():
     #           print("Duplicate")
      #          return is_open, children
        userTable = pd.read_sql_table('users', 'sqlite:///auth.sqlite')
        userTable = userTable[userTable['username'] == userName]
        ylist = ""
        print(str(userTable['graph'].iloc[0]))
        for element in y:
            ylist = ylist + "," + element
        currData = str(name) + "@" + fileName + "~" + str(type) + "~" + str(x) + "~" + ylist + "~" + str(color) + "~" + str(title) + "~" + str(xlabel) + "~" + str(ylabel) + "~" + str(theme) + "~" + str(marker) + "~" + str(prevQuery)
        info = str(userTable['graph'].iloc[0]) + ";" + currData
        print(info)
        try:
            sqliteConnection = sqlite3.connect('auth.sqlite')
            cursor1 = sqliteConnection.cursor()
            print("Connected to SQLite")
            sql_update_query = """UPDATE users SET graph=? WHERE username=?"""
            data = (info, userName)
            cursor1.execute(sql_update_query, data)
            sqliteConnection.commit()
            print("Record Updated successfully ")
            cursor1.close()

        except sqlite3.Error as error:
            print("Failed to update sqlite table", error)
        finally:
            if sqliteConnection:
                sqliteConnection.close()
                print("The SQLite connection is closed")

        #print(currData)
#html.A([html.Img(src='https://freepikpsd.com/file/2019/11/graph-icon-transparent-png-images-blue-.png', id='image', n_clicks=0)])
        if type == "Scatter":
            new_element = dbc.Button([html.Img(src='assets/scatter.PNG', 
                        style={'height': '10vh', 'width':'10vh', 'margin-left':'-2px'}), 
                        html.Label("{}".format(str(currData).split("@")[0]), style={'width':'10vh'})], id={
                'type': 'dynamic-graph',
                'index': "{}".format(str(currData))},
                n_clicks=0, style={'margin-right':'5px','width':'12vh', 'background-color':'#d6dbe0', 'font-size':'15px', 'text-align': 'center'}
                )
        elif type == "Line":
            new_element = dbc.Button([html.Img(src='https://www.iconbunny.com/icons/media/catalog/product/2/8/2888.8-frequency-graphs-icon-iconbunny.jpg', 
                        style={'height': '10vh', 'width':'10vh', 'margin-left':'-2px'}), 
                        html.Label("{}".format(str(currData).split("@")[0]), style={'width':'10vh'})], id={
                'type': 'dynamic-graph',
                'index': "{}".format(str(currData))},
                n_clicks=0, style={'margin-right':'5px','width':'12vh', 'background-color':'#d6dbe0', 'font-size':'15px', 'text-align': 'center'}
                )
        else:
            new_element = dbc.Button([html.Img(src='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAOEAAADhCAMAAAAJbSJIAAAAjVBMVEX///9ktfZCQkI/Pz/5+flUVFRXV1dcXFz///1es/Xp9v////n5//xVr/Sn0/z8/vvQ5vr1+fydzPVWsvvF4Phpsu52vPeq0vfz+vm02vxesvPb6/datPqk0fNnZ2f6///C4POVy++gzOmu1+xvvvqg1PGy1vB2vPh7uuxTq+3c8PbL4vHc6fDT6vTq9v6kA2RQAAADDklEQVR4nO3cgVbaMBSA4SLiUiuL2GFZRykydco23//xhmdux50GW1lC7m3/7wn6W6E3oW2SAAAAAAAAAAAAAAB2Tv8R+2hCWE1eWfUxcTJ+5UMfC8/GJ39RqBOF+lGoH4X6UagfhfpRqB+F+lGoH4X6NQpNbYxtkSV17OPurlnYQeyDfpdGYZ2sb65abGaKIpufw6zK0+XbRk+aC01SlKM2i1pPIoUUykchhfJRSKF8zbnUVGlb4HymaPp2zKWb6TR/W/mUaS5M6kUrTQtEx+cwaV0BWz1ncJC7GL1DoX4U6uco9DmvCLisuK74F63Xw84yW2fyCr8+XHtze30XOdBRaO/yuT/lvbhzaHZri7Yd4e5GeRX7o3jY+rC7ZWUppJBCCimkkEKRhWnrhml3ubzCOru/9TZ4f3u4vRc3tSWZsfbCl9pG3x1vFtaJybyJ3rfnjqHaG+N1x8BPYe9QqB+F+g2x0C4WswCi/fGa10NbPE69y6ef5RSaokw92y0xUlmF/pYWL+ajuaBCv+vDF6mkcxikcFRSSCGFFFJIYRtp10PfU1uaLgXNpUly2fZg1/tVNzeXYgqf98a6PKH3LrHq3IU2QKKNuDHsXOP7u2PoRay6vYW9QqF+jl9mTOb7i+aZnMLdsdTev2lifts4/kttlvW60Jjt+jKAczmFSeF/u3RHzlzK6olCCimkkEIKB1FoCo+3Jv4h6RfSxFTlyONDM7+JOoe2anlW/QBTUful2Xb9KYAvcgpjrsdDGOI+Td9QqB+F+jnmUmO8PYzQ4WmF4K+BcV4P/T2N0P64QvB3+Thmmu+b4uORFNXVNnCgc/LO/f+Ov0e5nP44+jkMtD7ct6oqg8+rFFJIIYUUUkjhIAuTDm/39JkYYWqzmzzID/lujz8DB7ruGJo9nR/Ndrs4/jmsQ9wRte9GqSO86XWAuxi9Q6F+FOo3tMLYRxPC68KTkzOxVp4Kx2JNPBWKNT6jkELpKKRQPgoplO8/Ciexx7GODp/aVhMdDp+8T7U4uBAAAAAAAAAAAAAAeuUXg+QS0KF/14gAAAAASUVORK5CYII=', 
                        style={'height': '10vh', 'width':'10vh', 'margin-left':'-2px'}), 
                        html.Label("{}".format(str(currData).split("@")[0]), style={'width':'10vh'})], id={
                'type': 'dynamic-graph',
                'index': "{}".format(str(currData))},
                n_clicks=0, style={'margin-right':'5px','width':'12vh', 'background-color':'#d6dbe0', 'font-size':'15px', 'text-align': 'center'}
                )
        #graphElement.append(data.strip())
        children.append(new_element)
        justSignedIn = True
        return not is_open, children

if __name__ == '__main__':
    app.run_server()
