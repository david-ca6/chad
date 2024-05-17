#!/usr/bin/env python3

# pip install -r requirements.txt

import os
import sys
import datetime
import warnings
import re

import requests
from bs4 import BeautifulSoup

import typer
from typing import List
from typing_extensions import Annotated

from chat_downloader import ChatDownloader

import dash
from dash import Dash, html, dcc, Input, Output, dash_table, State
import plotly.express as px
import plotly.graph_objects as go


import numpy as np
import pandas as pd
from pandas.errors import SettingWithCopyWarning

import webbrowser


from tabulate import tabulate

# ------------------------  ------------------------  ------------------------
# ------------ ------------------------  ------------------------ ------------
# Define the Software Information and setup the typer app
# ------------ ------------------------  ------------------------ ------------
# ------------------------  ------------------------  ------------------------

__SOFT_NAME__ = "CHat Activity Dashboard"
__SOFT_VERSION__ = "00.00.01"
__SOFT_COPYRIGHT__ = "Copyright 2024 CA6.DEV"
__SOFT_BRIEF__ = "This tool is used to Analyse Chat Activity in a Stream, and generate a Graph of the Chat Activity."
__SOFT_DESC__ = ""
__SOFT_CONTACT__ = "For more information, please visit https://ca6.dev"
__SOFT_EXTCOPYRIGHT__ = "MIT License, Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software. THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE."

sys.tracebacklimit = 20
pd.set_option('display.max_rows', None)
pd.set_option('display.max_colwidth', None)
warnings.simplefilter(action="ignore", category=UserWarning)
warnings.simplefilter(action="ignore", category=SettingWithCopyWarning)
# plt.style.use('dark_background')

app = typer.Typer(add_completion=False, pretty_exceptions_enable=False, help=__SOFT_BRIEF__)

dasher = dash.Dash(__name__)

# ------------------------  ------------------------  ------------------------
# ------------ ------------------------  ------------------------ ------------
# misc function
# ------------ ------------------------  ------------------------ ------------
# ------------------------  ------------------------  ------------------------

def time_formatMin(x, pos):
    return str(datetime.timedelta(minutes=x)).split(".")[0]

def time_formatSec(x, pos):
    return str(datetime.timedelta(seconds=x)).split(".")[0]

# ------------------------  ------------------------  ------------------------
# ------------ ------------------------  ------------------------ ------------
# Generic functions used to load/save data
# ------------ ------------------------  ------------------------ ------------
# ------------------------  ------------------------  ------------------------
def loadChat_fromURL(url: str):
    chat = ChatDownloader().get_chat(url)

    df = pd.DataFrame(columns=['time', 'timestamp', 'user', 'message'])
    starttime = 0
    started = False
    for message in chat:
        message_seconds = message.get("time_in_seconds")
        if (message_seconds < 0):
            continue
        if started == False:
            starttime = datetime.datetime.fromtimestamp(message.get("timestamp") / 1000 / 1000)
            started = True

        user = message.get("author").get("name")
        message_content = message.get("message")
        message_datetime = int(message.get("timestamp") / 1000 / 1000)
        duration = starttime - datetime.datetime.fromtimestamp(message_datetime)
        duration_in_minutes = abs(divmod(duration.total_seconds(), 60)[0])
        
        # add the message to the dataframe
        df.loc[len(df), ['time', 'timestamp', 'user','message']] = duration_in_minutes, abs(duration.total_seconds()), user, message_content

    return df

def loadChat_fromCSV(path: str):
    df = pd.read_csv(path, comment='#', engine='c')
    return df

def saveChat_toCSV(df, path: str):
    df.to_csv(path, index=False)
    return df;

def saveChat_toEditingCSV(df, path: str):
    return;

def saveMarker_toDaVinciEDL(df_edl, path: str):

    f = open(path, "w")
    f.write("TITLE: marker\n")
    f.write("FCM: NON-DROP FRAME\n\n")

    for index, row in df_edl.iterrows():
        f.write(str(int(index)+1) + "  001      V     C        " + str(row['start']) + " " + str(row['end']) + " " + str(row['start']) + " " + str(row['end']) + "\n")
        f.write(" |C:ResolveColor" + row['color'] + " |M:" + row['note'] + " |D:" + str(row["duration"]) + "\n\n")
    f.close()

def saveChat_toDaVinciEDL(df, path: str, color: str):
    df_edl = pd.DataFrame(columns=['start', 'end', 'note', 'color', 'duration'])

    for index, row in df.iterrows():
        start = time_formatSec(row['timestamp'], 0) + ":00"
        start = start.replace(':', '')
        start = start.zfill(8)
        start = start[:2] + ':' + start[2:4] + ':' + start[4:6] + ':' + start[6:]

        end = start
        note = row['message']
        colour = color
        duration = 1
        new_row = {'start': start, 'end': end, 'note': note, 'color': colour, 'duration': duration}
        df_edl.loc[len(df_edl)] = new_row

        saveMarker_toDaVinciEDL(df_edl, path)

    return;


def load_vodts_marker(path: str):
    # vodts format is one timestamp per line, h:mm:ss {type} {note}
    # where type is None for chapter, . for subchapter, .. for subchapter timestamp, ... for misc timestamp, .... for editor note

    df = pd.DataFrame(columns=['start', 'end', 'note', 'color', 'duration'])

    f = open
    with open(path, 'r') as f:
        i = 0
        for line in f:
            i = i+1
            if i<4:
                continue
            timeS = line.split(' ')[0]
            timeS = timeS + ":00"
            timeS = timeS.replace(':', '')
            timeS = timeS.zfill(8)
            timeS = timeS[:2] + ':' + timeS[2:4] + ':' + timeS[4:6] + ':' + timeS[6:]


            timeE = timeS

            note = line.split(' ', 1)[1]
            note = note.replace('\n', '')

            color = 'Yellow'
            if(note.startswith('....')):
                color = 'Blue'
                note = note[5:]
            elif(note.startswith('...')):
                color = 'Red'
                note = note[4:]
            elif(note.startswith('..')):
                color = 'Purple'
                note = note[3:]
            elif(note.startswith('.')):
                color = 'Green'
                note = note[2:]

            new_row = {'start': timeS, 'end': timeE, 'note': note, 'color': color, 'duration': 1}
            df.loc[len(df)] = new_row

    return df

def get_youtube_title(url: str):
    
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # get the title of the video
    if soup.title:
        title = soup.title.string.replace(' - YouTube', '')
    else:
        title = None

    return title

def get_twitch_title(url: str):
    
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # get the title of the video
    meta_tag = soup.find('meta', property='og:title')
    if meta_tag:
        title = meta_tag['content']
    else:
        title = None

    return title

def webScraping(url: str):

    # if youtube, get the title of the video
    if "youtube" in url:
        title = get_youtube_title(url)
    elif "twitch" in url:
        title = get_twitch_title(url)
    else:
        title = None
    return title;

# ------------------------  ------------------------  ------------------------
# ------------ ------------------------  ------------------------ ------------
# Processing functions used to process the data
# ------------ ------------------------  ------------------------ ------------
# ------------------------  ------------------------  ------------------------

def printChat_withURL(url, df):#
    # print the chat messages with the URL+timestamp
    print("Chat Messages from " + url)

    # extract the last part of the url

    # get the platform
    if "youtube" in url:
        # https://www.youtube.com/watch?v=yFG5AJ38p6U
        # get the video id
        vidId = url.split("=")[-1]

        # https://youtu.be/yFG5AJ38p6U?t=2127
        tsurl = "https://youtu.be/" + vidId + "?t="
        platform = "youtube"
    elif "twitch" in url:
        vidId = url.split("/")[-1]
        # https://www.twitch.tv/videos/2139118880?t=04h21m03s
        tsurl = "https://www.twitch.tv/videos/" + vidId + "?t="
        platform = "twitch"
    else:
        return
    
    dff = pd.DataFrame(columns=['time', 'user', 'message', 'url'])

    for index, row in df.iterrows():
        # convert the timestamp to a string HH:mm:ss
        timestamp = str(datetime.timedelta(seconds=row['timestamp'])).split(".")[0]

        if platform == "youtube":
            tsurlts = tsurl + str(int(row['timestamp']))
        elif platform == "twitch":
            tsurlts = tsurl + timestamp.split(":")[0] + "h" + timestamp.split(":")[1] + "m" + timestamp.split(":")[2] + "s"

        dff.loc[len(dff), ['time', 'user','message', 'url']] = timestamp, row['user'], row['message'], tsurlts
    

    dff['url'] = dff['url'].apply(lambda x: f"[Click Here]({x})")
    return dff

def printChat(df):
    print(tabulate(df, headers='keys', tablefmt='plain', stralign='left', numalign='left'))
    return;

def addUrlToChat(url, df):

    if "youtube" in url:
        # https://www.youtube.com/watch?v=yFG5AJ38p6U
        # get the video id
        vidId = url.split("=")[-1]

        # https://youtu.be/yFG5AJ38p6U?t=2127
        tsurl = "https://youtu.be/" + vidId + "?t="
        platform = "youtube"
    elif "twitch" in url:
        vidId = url.split("/")[-1]
        # https://www.twitch.tv/videos/2139118880?t=04h21m03s
        tsurl = "https://www.twitch.tv/videos/" + vidId + "?t="
        platform = "twitch"
    else:
        return
    
    # add the url with timestamp to the dataframe
    for index, row in df.iterrows():
        # convert the timestamp to a string HH:mm:ss
        timestamp = str(datetime.timedelta(seconds=row['timestamp'])).split(".")[0]

        if platform == "youtube":
            tsurlts = tsurl + str(int(row['timestamp']))
        elif platform == "twitch":
            tsurlts = tsurl + timestamp.split(":")[0] + "h" + timestamp.split(":")[1] + "m" + timestamp.split(":")[2] + "s"

        df.loc[index, 'timestamps'] = timestamp
        df.loc[index, 'url'] = tsurlts

    return df;

# ------------------------  ------------------------  ------------------------
# ------------ ------------------------  ------------------------ ------------
# Terminal functions called by the user
# ------------ ------------------------  ------------------------ ------------
# ------------------------  ------------------------  ------------------------

def filter_data(df, start: str, end: str, keyword: str, user: str):
    df['keywordFound'] = None
    if keyword and len(keyword) > 0:
        df = df[df['message'].str.contains(keyword, case=False, regex=True)]
        df['keywordFound'] = df['message'].str.extract("(" + "|".join(keyword) + ")", flags=re.IGNORECASE)
    if user and len(user) > 0:
        df = df[df['user'].str.contains("^(" + user + ")$", case=False)]
    if start:
        df = df[(df['time'] >= int(start))]
    if end:
        df = df[(df['time'] <= int(end))]
    return df

@dasher.callback(
    [Output('zoom-level-info', 'children'), Output('table-div', 'children', allow_duplicate=True)],
    Input('output-graph', 'relayoutData'),
    Input('store-data', 'data'),
    [State('input-keyword', 'value'),
     State('input-user', 'value')],
    prevent_initial_call=True
)
def display_zoom_level(relayoutData, stored_data, keyword, user):

    if stored_data is not None:
        urlo = stored_data['url']
        data_json = stored_data['data']
        dfo = pd.read_json(data_json, orient='split')

    x_range_start = dfo['time'].min()
    x_range_end = dfo['time'].max()

    if relayoutData:
        if 'xaxis.range[0]' in relayoutData and 'xaxis.range[1]' in relayoutData:
            x_range_start = relayoutData['xaxis.range[0]']
            x_range_end = relayoutData['xaxis.range[1]']

    if stored_data is not None and x_range_start is not None and x_range_end is not None:

        filtered_df3 = dfo
        filtered_df3 = filter_data(dfo, x_range_start, x_range_end, keyword, user)
        df3 = filtered_df3.groupby("time")["keywordFound"].count().reset_index(name="keyword_per_minute")

        table = None
        if filtered_df3 is not None:
            filtered_df3 = addUrlToChat(urlo, filtered_df3)

            filtered_df3['url'] = filtered_df3['url'].apply(lambda x: f"[Link]({x})")

            filtered_df3 = filtered_df3[['time', 'timestamps', 'message', 'url']]

            table = dash_table.DataTable(
                data=filtered_df3.to_dict('records'),
                columns=[{"name": i, "id": i, 'type': 'text', 'presentation': 'markdown'} if i == 'url' else {"name": i, "id": i} for i in filtered_df3.columns],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left'},
                markdown_options={"html": True, "link_target": "_blank"}
            )
        return "Zoom or pan to update the view.", table

    return "No zoom update detected.", None

@dasher.callback(
    Output('url-output', 'children'),  # Placeholder output, necessary for callback
    Output('iframe-video', 'src'),  # Add this output to update the iframe src
    Input('output-graph', 'clickData')
)
def open_url(clickData):
    if clickData:
        url = clickData['points'][0]['customdata']
        embed_url = ""

        if "youtube" in url:
            vid_id = url.split("v=")[-1].split("&")[0]
            timestamp = int(url.split("t=")[-1])
            embed_url = f"https://www.youtube-nocookie.com/embed/{vid_id}?autoplay=1&start={timestamp}&rel=0&vq=hd1080"
        elif "youtu.be" in url:
            vid_id = url.split("/")[-1]
            timestamp = int(url.split("t=")[-1])
            embed_url = f"https://www.youtube-nocookie.com/embed/{vid_id}?autoplay=1&start={timestamp}&rel=0&vq=hd1080"
        elif "twitch" in url:
            vid_id = url.split("/")[-1].split("?")[0]
            timestamp = url.split("t=")[-1]
            # <iframe src="https://player.twitch.tv/?video=2146413500&time=0h51m2s&parent=127.0.0.1" frameborder="0" allowfullscreen="true" scrolling="no" height="378" width="620"></iframe>
            embed_url = f"https://player.twitch.tv/?video={vid_id}&time={timestamp}&parent=127.0.0.1"  # Change "localhost" to your domain if necessary
        else:
            embed_url = ""

        # webbrowser.open(url)  # Open URL in the default web browser, removed, we now use embed

        return f"Opened: {url}", embed_url
    return "Click on a bar to open the URL.", ""


@dasher.callback(
    Output('store-data', 'data'),
    Input('fetch-button', 'n_clicks'),
    State('input-url', 'value'),
    prevent_initial_call=True
)
def fetch_and_store_data(n_clicks, url):
    print("fetch")
    if url:
        df = loadChat_fromURL(url)
        data_json = df.to_json(date_format='iso', orient='split')
        return {'url': url, 'data': data_json}
    return dash.no_update

@dasher.callback(
    [Output('output-graph', 'figure'), Output('table-div', 'children', allow_duplicate=True)],
    Input('submit-button', 'n_clicks'),
    Input('store-data', 'data'),
    [State('input-url', 'value'),
     State('input-keyword', 'value'),
     State('input-user', 'value'),
     State('input-start-time', 'value'),
     State('input-end-time', 'value')],
    prevent_initial_call=True
)
def update_output(n_clicks, stored_data, url, keyword, user, start_time, end_time):
    if stored_data:
        print("process")
        urlo = stored_data['url']
        data_json = stored_data['data']
        dfo = pd.read_json(data_json, orient='split')

        title = webScraping(urlo)

        filtered_df2 = filter_data(dfo, start_time, end_time, None, None)
        df2 = filtered_df2.groupby("time")["time"].count().reset_index(name="chat_per_minute")
        df2['timestamp'] = df2['time'].astype(float)*60
        df2 = addUrlToChat(urlo, df2)
        # df2['url'] = df2['url'].apply(lambda x: f"[Link]({x})")


        filtered_df3 = dfo
        if keyword is not None and len(keyword) > 0:
            filtered_df3 = filter_data(dfo, start_time, end_time, keyword, user)
            df3 = filtered_df3.groupby("time")["keywordFound"].count().reset_index(name="keyword_per_minute")
        else:
            df3 = pd.DataFrame(columns=['time', 'keyword_per_minute'])

        # merge df3['keyword_per_minute'] colum and df2['chat_per_minute'] colum in an df['activity'] colum using time as the key
        df = pd.merge(df2, df3, on="time", how="outer")
        df['keyword_per_minute'] = df['keyword_per_minute'].fillna(0)
        df['chat_per_minute'] = df['chat_per_minute'].fillna(0)
        df['activity'] = df['keyword_per_minute'] + df['chat_per_minute']


        trace0 = go.Bar(x=df['time'], y=df['activity'], name='Combined Activity', marker_color='red')
        trace1 = go.Bar(x=df2['time'], y=df2['chat_per_minute'], name='Chat Activity', marker_color='green', customdata=df2['url'], hovertemplate="<b>Time:</b> %{x}<br><b>Chats Per Minute:</b> %{y}<br><b>URL:</b> %{customdata}<extra></extra>")
        trace2 = go.Bar(x=df3['time'], y=df3['keyword_per_minute'], name='Keyword Activity', marker_color='blue')

        fig = go.Figure(data=[trace0, trace1, trace2])
        fig.update_layout(
            barmode='overlay',  # Ensure histograms overlap
            title_text=title,
            xaxis_title_text='Time (minutes)',
            yaxis_title_text='Count',
        )

        table = None
        if filtered_df3 is not None:
            filtered_df3 = addUrlToChat(urlo, filtered_df3)

            filtered_df3['url'] = filtered_df3['url'].apply(lambda x: f"[Link]({x})")
            filtered_df3 = filtered_df3[['time', 'timestamps', 'message', 'url']]

            table = dash_table.DataTable(
                data=filtered_df3.to_dict('records'),
                columns=[{"name": i, "id": i, 'type': 'text', 'presentation': 'markdown'} if i == 'url' else {"name": i, "id": i} for i in filtered_df3.columns],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left'},
                markdown_options={"html": True, "link_target": "_blank"}
            )
        return fig, table
    return go.Figure()

@app.command(rich_help_panel="Commands", help="Chat Activity Analyzer, if Keywords or Users are provided, it will filter the data.")
def serve():

    dasher.layout = html.Div([
        html.Script(src="https://www.youtube.com/iframe_api"),
        html.Div([
            html.H1(__SOFT_NAME__ + " " + __SOFT_VERSION__),
            dcc.Store(id='store-data', storage_type='session'),

            dcc.Input(id='input-url', type='text', placeholder='Enter URL'),
            html.Button('Fetch Data', id='fetch-button', n_clicks=0),
            html.Br(),
            dcc.Input(id='input-keyword', type='text', placeholder='Enter keyword'),
            dcc.Input(id='input-user', type='text', placeholder='Enter user'),
            dcc.Input(id='input-start-time', type='text', placeholder='Start Time'),
            dcc.Input(id='input-end-time', type='text', placeholder='End Time'),
            html.Button('Run', id='submit-button', n_clicks=0),
        ]),
        dcc.Graph(id='output-graph'),
        html.Div(id='url-output'),
        html.Div([
            html.Iframe(id='iframe-video', style={'width': '45%', 'height': '390px', 'display': 'inline-block'}, allow="autoplay; fullscreen"),
            html.Textarea(id='note-area', style={'width': '45%', 'height': '390px', 'display': 'inline-block', 'resize': 'none'}, placeholder='Enter your notes here...'),
        ],  style={'textAlign': 'center'}),
        html.Div(id='table-div'),

        # garbage at the bottom
        html.Div(id='zoom-level-info')
    ])
    
    dasher.index_string = '''
        <!DOCTYPE html>
        <html>
            <head>
                <title>''' + __SOFT_NAME__ + '''</title>
                <link rel="stylesheet" href="/static/style.css">
                <script src="/static/script.js"></script>
            </head>
            <body>
                {%app_entry%}
                <footer>
                    {%config%}
                    {%scripts%}
                    {%renderer%}
                </footer>
            </body>
        </html>
        '''


    dasher.run_server(debug=True)
    return

# extract all chats that contain a specific keyword
# @app.command(rich_help_panel="Commands", help="Chat Activity Analyzer, if Keywords or Users are provided, it will filter the data.")
# def chat(
#                     # input options
#                     use_url: Annotated[str, typer.Option(rich_help_panel="Input Options", help="URL of the stream (Slower)")] = None,
#                     use_csv: Annotated[str, typer.Option(rich_help_panel="Input Options", help="Use a csv source for the chat instead of downloading it (faster)")] = None,

#                     # filter options
#                     keyword: Annotated[List[str], typer.Option(rich_help_panel="Filter Options", help="Keyword to search for (can be used multiple times)")] = None,
#                     user: Annotated[List[str], typer.Option(rich_help_panel="Filter Options", help="User to search for (can be used multiple times)")] = None,
#                     start_time: Annotated[str, typer.Option(rich_help_panel="Filter Options", help="Start Time Filter")] = None,
#                     end_time: Annotated[str, typer.Option(rich_help_panel="Filter Options", help="End Time Filter")] = None,

#                     # plot options
#                     plot_marker: Annotated[List[str], typer.Option(rich_help_panel="Plot Options", help="Add a vertical line marker to the plot at the given time, \"hh:mm:ss message\"")] = None,
#                     use_vodts: Annotated[str, typer.Option(rich_help_panel="Plot Options", help="Load plot marker from a vodts files (only chapters are used)")] = None,

#                     # general output options
#                     save_csv: Annotated[str, typer.Option(rich_help_panel="Output Options", help="Save the filtered chat to a csv file")] = None,
#                     plot: Annotated[bool, typer.Option(rich_help_panel="Output Options", help="Plot an histogram of the chat activity")] = False,
#                     output: Annotated[bool, typer.Option(rich_help_panel="Output Options", help="Print the keyword activity in the terminal")] = False,

#                     # DaVinci Resolve EDL options
#                     save_edl: Annotated[str, typer.Option(rich_help_panel="Output Options", help="Save the filtered chats to a DaVinci Resolve EDL file")] = None,
#                     edl_color: Annotated[str, typer.Option(rich_help_panel="Output Options", help="Color of the markers in the EDL file")] = "Yellow",
#                 ):
    
#     if use_url is None and use_csv is None:
#         print("Please provide a stream URL or a csv file.")
#         return
    
#     if use_csv:
#         df = loadChat_fromCSV(use_csv)
#         vidTitle = None

#         # get the url from the csv file comment '# URL: '
#         with open(use_csv, 'r') as f:
#             for line in f:
#                 if line.startswith("# URL: "):
#                     stream_url = line.split("# URL: ")[1].split("\n")[0]
#                     break
#         vidId = stream_url.split("=")[-1].split("/")[-1]


#         # get the video title from the csv file comment '# TITLE: '
#         with open(use_csv, 'r') as f:
#             for line in f:
#                 if line.startswith("# TITLE: "):
#                     vidTitle = line.split("# TITLE: ")[1].split("\n")[0]
#                     break
#     else:
#         stream_url = use_url
#         df = loadChat_fromURL(stream_url)
#         vidTitle = webScraping(stream_url)
#         vidId = stream_url.split("=")[-1].split("/")[-1]

#     # remove the message that are NaN
#     df = df.dropna(subset=['message'])

#     if keyword is None:
#         df1 = df
#     else:
#         # filter the dataframe to only show the user, case insensitive, and add the keywordFound column containing the keyword that was found
#         escaped_keywords = [re.escape(kwd) for kwd in keyword]
#         pattern = "|".join(escaped_keywords)
#         df1 = df[df['message'].str.contains(pattern, case=False, regex=True)]
#         df1['keywordFound'] = df1['message'].str.extract("(" + "|".join(keyword) + ")", flags=re.IGNORECASE)

#         print("|".join(keyword))

#     if user is not None:
#         # filter the dataframe to only show the user, case insensitive, need a full match, partial match is not supported
#         escaped_users = [re.escape(usr) for usr in user]
#         pattern = "|".join(escaped_users)
#         df1 = df1[df1['user'].str.contains("^(" + pattern + ")$", case=False)]

#     if start_time is not None:
#         df1 = df1[df1['time'] >= int(start_time)]

#     if end_time is not None:
#         df1 = df1[df1['time'] <= int(end_time)]

#     average_chat_per_minute = 0
#     average_marker_per_minute = 0

#     # calculate the average_chat_per_minute
#     df2 = df.groupby("time")["time"].count().reset_index(name="chat_per_minute")
#     average_chat_per_minute = df2["chat_per_minute"].mean()

#     # calculate the average_marker_per_minute
#     if keyword is not None:
#         df3 = df1.groupby("time")["keywordFound"].count().reset_index(name="keyword_per_minute")
#         average_marker_per_minute = df3["keyword_per_minute"].mean()

#     if save_csv:
#         df1.to_csv(save_csv, index=False)
#         with open(save_csv, 'a') as f:
#             f.write('# TITLE: ' + vidTitle + '\n')
#             f.write('# URL: ' + stream_url + '\n')

#     dffu = printChat_withURL(stream_url, df1)

#     dfmk = None
#     if use_vodts is not None:
#         dfmk = load_vodts_marker(use_vodts)

#     if save_edl:
#         saveChat_toDaVinciEDL(df1, save_edl, edl_color)

#     print(vidTitle)
#     print(stream_url)

#     if plot:
#         trace1 = go.Bar(x=df2['time'], y=df2['chat_per_minute'], name='Chat Activity', marker_color='green')
#         trace2 = go.Bar(x=df3['time'], y=df3['keyword_per_minute'], name='Keyword Activity', marker_color='blue')

#         fig = go.Figure(data=[trace1, trace2])
#         fig.update_layout(
#             barmode='overlay',  # Ensure histograms overlap
#             title_text='Chat and Keyword Activity Over Time',
#             xaxis_title_text='Time (minutes)',
#             yaxis_title_text='Count',
#         )

#         # fig = px.histogram(df2, x='time' , y='chat_per_minute', title='Chat Activity of ' + vidTitle, labels={'time': 'Time (minutes)', 'chat_per_minute': 'Chat Activity'}, color_discrete_sequence=['#FFA07A'])

#         dasher.layout = html.Div([
#             html.H1(__SOFT_NAME__ + " " + __SOFT_VERSION__),
#             html.H2(vidTitle),

#             dcc.Input(id='input-keyword', type='text', placeholder='Enter a keyword...'),
#             dcc.Graph(
#                 id='example-graph',
#                 figure=fig
#             ),
#             dash_table.DataTable(
#                 id='table',
#                 columns=[{"name": i, "id": i, 'type': 'text', 'presentation': 'markdown'} if i == 'url' else {"name": i, "id": i} for i in dffu.columns],
#                 data=dffu.to_dict('records'),
#                 page_size=50,
#                 markdown_options={"html": True, "link_target": "_blank"}  # Allows HTML and opens links in a new tab
#             )
#         ])


#         dasher.run_server(debug=False)

#     return;

# ------------------------  ------------------------  ------------------------

@app.command(rich_help_panel="Commands", help="Command used to convert a vodts file to a DaVinci Resolve EDL file.")
def vodts2edl(       path: str = typer.Argument(help="URL of the stream"),
                    save_edl: str = typer.Argument(help="URL of the stream"),

                    save_csv: Annotated[str, typer.Option(rich_help_panel="Chat Options", help="Save the markers to a csv file")] = None,
                ):
    
    df = load_vodts_marker(path)
    saveMarker_toDaVinciEDL(df, save_edl)
    df.to_csv(save_csv, index=False)

    return;

# ------------------------  ------------------------  ------------------------
# ------------ ------------------------  ------------------------ ------------
# main, callback functions, ...
# ------------ ------------------------  ------------------------ ------------
# ------------------------  ------------------------  ------------------------

def version_callback(value: bool):
    if value:
        print(__SOFT_VERSION__)
        raise typer.Exit()

def about_callback(value: bool):
    if value:
        print(__SOFT_NAME__ + " " + __SOFT_VERSION__)
        print(__SOFT_COPYRIGHT__)
        print(__SOFT_BRIEF__)
        print("")
        print(__SOFT_DESC__)
        print("")
        print(__SOFT_CONTACT__)
        print(__SOFT_EXTCOPYRIGHT__)
        raise typer.Exit()

@app.callback()
def main(
    version: bool = typer.Option(None, "--version", callback=version_callback, is_eager=True, help="Display version number"),
    about: bool = typer.Option(None, "--about", callback=about_callback, is_eager=True, help="Display Informations About " + __SOFT_NAME__),
):
    return

if __name__ == "__main__":
    if 'COLAB_GPU' in os.environ:
        serve()                     # in google colab, we run the dashboard directly
    else:
        app()                       # shell instance, we run with typer