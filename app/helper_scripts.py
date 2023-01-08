import json
import pandas as pd 
import requests 
from datetime import date, timedelta
import re
from bs4 import BeautifulSoup
import boto3
from streamlit_echarts import st_echarts
import streamlit as st



# use this to pull latest Athena file.
def fn_from_s3(filename,bucketIN):
    
    s3 = True
    
    if s3:
        session = boto3.Session()
        s3_client = session.client("s3")
        response = s3_client.get_object(Bucket=bucketIN, Key=filename)

        status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")

        if status == 200:
            #print(f"Successful S3 get_object response. Status - {status}")
            dfOUT = pd.read_csv(response.get("Body"))
            return dfOUT
        else:
            #print(f"Unsuccessful S3 get_object response. Status - {status}")
            return pd.DataFrame()
    else:
        
        return pd.read_csv(filename)


def to_s3(bucket, dfIN, file_path,file_type):
    
    s3 = False 
    
    if s3:
        if file_type=='HTML':
            
            try:
                html_file = dfIN
                s3_resource = boto3.resource('s3')
                s3_resource.Object(bucket, file_path).put(Body=html_file)
                print(f'SUCCESS: Saved path {file_path}')
            except:
                print ('unable to save')
            
        
        elif file_type == 'CSV':        
            try:
                csv_buffer = StringIO()
                dfIN.to_csv(csv_buffer, index=False)
                s3_resource = boto3.resource('s3')
                s3_resource.Object(bucket, file_path).put(Body=csv_buffer.getvalue())
                print(f'SUCCESS: Saved path {file_path}')
            except:
                print (f'unable to save {file_path}')
    
    else:
        
        dfIN.to_csv(file_path)
        st.write(f'{file_path} saved locally')
        
            
                

def render_basic_tree():
    with open("./data/flare.json", "r") as f:
        data = json.loads(f.read())
        st.write(data)

    for idx, _ in enumerate(data["children"]):
        data["children"][idx]["collapsed"] = idx % 2 == 0

    option = {
        "tooltip": {"trigger": "item", "triggerOn": "mousemove"},
        "series": [
            {
                "type": "tree",
                "data": [data],
                "top": "1%",
                "left": "7%",
                "bottom": "1%",
                "right": "20%",
                "symbolSize": 7,
                "label": {
                    "position": "left",
                    "verticalAlign": "middle",
                    "align": "right",
                    "fontSize": 9,
                },
                "leaves": {
                    "label": {
                        "position": "right",
                        "verticalAlign": "middle",
                        "align": "left",
                    }
                },
                "emphasis": {"focus": "descendant"},
                "expandAndCollapse": True,
                "animationDuration": 550,
                "animationDurationUpdate": 750,
            }
        ],
    }
    st_echarts(option, height="500px")


def fn_build_tree_element(nameIN, childItems):
    
    return True 

def fn_return_board(symbol):
    
    today = date.today()
    
    URL = "https://www.marketwatch.com/investing/stock/"+symbol+"/company-profile?mod=mw_quote_tab"
#     page = requests.get(URL)
#     soup = BeautifulSoup(page.content, 'html.parser')
#     results = soup.select('ul[class="list list--kv"]')
    
    pattern = 'ul[class="list list--kv"]'
    results = fn_get_url(URL,pattern)
    
    #print(results)
    
    
    df_members = pd.DataFrame()
    
    try:

        boardmembers = results[0].select('li')
        
        for anchor in boardmembers:
            board_member_url = anchor.find('a')['href']
            board_member_name = anchor.find('a').text
            board_member_title = anchor.find('small').text
            
            # Get board_member profile text by mining the specific URL for their profile
            
            pattern = 'div[class="element element--text biography"]'
            profile_results = fn_get_url(board_member_url,pattern)
            
           # print(profile_results)
        
            profile_text = ''
            for x in profile_results[0].select('p'):
                profile_text += x.text

            attribute_list = {'board_member_url':board_member_url,
                              'board_member_name':board_member_name,
                              'board_member_profile':profile_text,
                              'board_member_title':board_member_title,
                              'last_updated':today,
                              'status':'success',
                              'ticker_symbol':symbol} 
            
   
            
            df_members = df_members.append(attribute_list, ignore_index = True)
    
            
    except:
        print("fail")
        attribute_list = {'board_member_url':'',
                          'board_member_name':'',
                          'board_member_title':'',
                          'board_member_profile':'',
                          'last_updated':today,
                          'status':'fail',
                          'ticker_symbol':symbol} 
        
        df_members = df_members.append(attribute_list, ignore_index = True)
    
            
    return df_members


def fn_return_ticker_descriptors(symbol):
    
    URL = "https://www.marketwatch.com/investing/stock/"+symbol+"/company-profile?mod=mw_quote_tab"
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, 'html.parser')
    results = soup.select('div[class="element element--text at-a-glance has-background background--blue"]')
    
    st.write(f'Pull {symbol} company profile ')
    
    try:
        #print('Great! ' + URL)
        address1 = results[0].select('div[class="address__line"]')[0].contents[0]
        address2 = results[0].select('div[class="address__line"]')[1].contents[0]
        
        try:
            address3 = (results[0].select('div[class="address__line"]')[2].contents[0])
        except:
            address3 = ''

        try:
            address4 = (results[0].select('div[class="address__line"]')[3].contents[0])
        except:
            address4 = ''

        
        phone = results[0].find_all('span')[1].contents[0]
        industry = results[0].find_all('span')[2].contents[0]
        sector = results[0].find_all('span')[3].contents[0]
        fiscal_year = results[0].find_all('span')[4].contents[0]
        revenue_2020 = results[0].find_all('span')[5].contents[0]
        netincome_2020 = results[0].find_all('span')[6].contents[0]
        sales_growth_2020 = results[0].find_all('span')[7].contents[0]
        employees_2020 = results[0].find_all('span')[8].contents[0]

        attribute_list = {'address1':address1,
                          'address2':address2,
                          'address3':address3,
                          'address4':address4,
                          'phone':phone,
                          'symbol':symbol,
                          'company_sector':sector,
                          'industry':industry,
                          'fiscal_year':fiscal_year,
                          'revenue':revenue_2020,
                          'netincome':netincome_2020,
                          'sales_growth':sales_growth_2020,
                          'employees':employees_2020
                         }
        
    except:
        attribute_list = {'address1':'FAIL',
                          'address2':'',
                          'address3':'',
                          'address4':'',
                          'phone':'',
                          'symbol':symbol,
                          'company_sector':'',
                          'industry':'',
                          'fiscal_year':'',
                          'revenue':'',
                          'netincome':'',
                          'sales_growth':'',
                          'employees':''
                         }
    
    attribute_list = pd.DataFrame.from_dict(attribute_list, orient='index')
    #st.write(attribute_list)
    return attribute_list[0]


def fn_get_url(URL,pattern):
    
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, 'html.parser')
    results = soup.select(pattern)
    
    return results
