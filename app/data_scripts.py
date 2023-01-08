# # https://towardsdatascience.com/using-python-to-work-with-amazon-dynamo-db-b00dc07c158
from boto3.dynamodb.conditions import Key
import seaborn as sns
import matplotlib.pyplot as plt
import boto3 
import json
import pandas as pd
import helper_scripts as hs 
import streamlit as st
from streamlit_echarts import st_echarts
import altair as alt
import time 
import os
from os import path
from datetime import datetime, timedelta

'''
Class allows connection dynamo db
''' 
class dtable:
    db = None
    tableName = None
    table = None
    table_created = False
    def __init__(self, connectionType):
        
        if connectionType == "Local":
            self.db  = boto3.resource('dynamodb',
            endpoint_url="http://localhost:8000")
        
        if connectionType == "AWS":
            self.db = boto3.resource('dynamodb')
        
        print(f"Initialized {connectionType}")
    
    def table_connection(self,tableName):
        table = self.db.Table(tableName)
        self.table = table
        print(f'Connected to table {self.table}')
        
     
    def createTable(self, tableName , KeySchema, AttributeDefinitions, ProvisionedThroughput):
        self.tableName = tableName
        table = self.db.create_table(
        TableName=tableName,
        KeySchema=KeySchema,
        AttributeDefinitions=AttributeDefinitions,
        ProvisionedThroughput=ProvisionedThroughput
        )
        self.table = table
        print(f'Created Table {self.table}')
    
    def deleteTable(self, tableName):
        
        try: 
            self.db.Table(tableName).delete()
            print(f'Existing {tableName} table deleted!')
        except:
            print(f'Unable to delete{tableName}')
     
    def insert_data(self, path):
        with open(path) as f:
            data = json.load(f)
            for item in data:
                try:
                    self.table.put_item(Item = item)
                except Exception as e:
                    print(e)            
        #print(f'Inserted Data into {self.tableName}')
        
    def table_scan(self):
        try:
            response = self.table.scan()    
            data = response['Items']
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                data.extend(response['Items'])
            return data
        except:
            print('Scan failed')
            return None
            
         
    # formats the dataframe as a the proper json format for loading    
    def insert_df(self, dfIN):
        try:
            dfIN.rename(columns={'year':'year_id','month':'month_id','day':'day_id'}, inplace=True)
        except:
            pass       
        json_str = dfIN.to_json(orient='table')
        data = json.loads(json_str)
        data = data['data']
        for item in data:
            try:
                self.table.put_item(Item = item)
            except Exception as e:
                print(e)            
        #print(f'Inserted Data into {self.tableName} from DataFrame')
    
    def getItem(self,key):
        response = self.table.get_item(Key = key)
        #print(response)
        try:
            response = self.table.get_item(Key = key)
            return response['Item']
        except Exception as e:
            print('Item not found')
            return None
        
        
    # snippet-end:[python.example_code.dynamodb.GetItem]
    
    def updateItem(self,key, updateExpression, conditionExpression,expressionAttributeValues):
        
        print(expressionAttributeValues)
        
        try:
            response = self.table.update_item(
            Key=key,
            UpdateExpression = updateExpression,
            ConditionExpression = conditionExpression,
            ExpressionAttributeValues = expressionAttributeValues,
           # ReturnValues="UPDATED_NEW"
            )
        
        except Exception as e:
            print(e)
            return None
        
        
    def deleteItem(self, key, conditionExpression, expressionAttributes):
        try:
            response = self.table.delete_item(
            Key = key,
            ConditionExpression = conditionExpression,
            ExpressionAttributeValues = expressionAttributes
        )
        except Exception as e:
            print(e)
    
    def query(self,projectExpression,expressionAttributes,keyExpression):
        try:
            response = self.table.query(
            ProjectionExpression = projectExpression,
            KeyConditionExpression= keyExpression,
            )
            return response['Items']
        except Exception as e:
            print(e)
            return None
       
# creates the dynamo db table - either in local or AWS depending on classObj passed through as variable. 
# If an initial dataframe is provided on instantiation, it is use to also populate the newly created table
def fn_create_db_obj(tableName, classObj, initial_df, primaryKeyIN, AttributeDataTypeIN, delete_table ):
    # ---
    # 0 Initializes table
    # --- 

    tableObj = classObj

    # --- 
    #   1 Configure table
    # ---

    primaryKey=primaryKeyIN

    AttributeDataType=AttributeDataTypeIN

    ProvisionedThroughput={
      'ReadCapacityUnits': 10,
      'WriteCapacityUnits': 10
    }

    #try to drop the table if it exists so we can start fresh
    
    if delete_table == True:
        try:
            tableObj.deleteTable(tableName)
        except:
            pass

    try:
        tableObj.createTable(
        tableName=tableName,
        KeySchema=primaryKey,
        AttributeDefinitions=AttributeDataType,
        ProvisionedThroughput=ProvisionedThroughput)
        print(f'{tableName} table created')
    except:
        pass


    # --- 
    #   2 populates tehe table, if it exists.
    # ---
    if initial_df:
      tableObj.insert_df(initial_df)
      print("-- \n")
        
    #print("Before Update")

    #print(tableObj.getItem(key = {'year_id' : year_id , 'company': ticket_symbol}))
    #print("-- \n")
    
    return tableObj
    
    
def fn_return_tickers():
    company_aws_tbl = dtable('AWS')
    company_aws_tbl.table_connection('company_aws_tbl')
    company_df  = pd.DataFrame(company_aws_tbl.table_scan())
    company_df.describe() 
    return company_df 
    
def fn_return_urls():
    url_aws_tbl = dtable('AWS')
    url_aws_tbl.table_connection('url_aws_tbl')
    url_df = pd.DataFrame(url_aws_tbl.table_scan())
    url_df.describe()
    return url_df 
    
def fn_percent(x,y):
    
    try:
        val = round((x/y)* 100,0)
    except:
        val = 0 
    return val     
    

def fn_return_athena_query():

    static_file = '586b76f3-ebb7-40b1-8142-88eb8985d2c9'
    #st.write(static_file)
    if static_file:
        
        df_athena = hs.fn_from_s3(f"{static_file}.csv",'jm-athena-outputs')
    
    else: 
        
        tableName = 'cesprocessed'
        dbName = 'csv_transcripts_db'
        labelIn = 'Environmental' # 'Governance' # 'Social'

        client = boto3.client('athena')
        queryStart = client.start_query_execution(
        QueryString = f"SELECT * FROM {tableName} WHERE (cast(score as double) BETWEEN 0.80 AND 0.99) AND label = '{labelIn}' ",
            QueryExecutionContext = {
                'Database': f'{dbName}'
            }, 
            ResultConfiguration = { 'OutputLocation': 's3://jm-athena-outputs'}
        )

        queryExecution = client.get_query_execution(QueryExecutionId=queryStart['QueryExecutionId'])
        execution_id = queryStart["QueryExecutionId"]
        st.write(execution_id)

        # Wait until the query is finished
        while True:
            try:
                client.get_query_results(QueryExecutionId=execution_id)
                break
            except Exception as e:
                print(f'{e} Athena response')
                time.sleep(10)

        df_athena = hs.fn_from_s3(f"{execution_id}.csv",'jm-athena-outputs')

    return df_athena


def fn_replace_discourse_item(s):
    
    replacement_elements = [
        '|',
        'President &',
        'President and',
        'President',
        'Executive',
        'Chief',
        'Deputy',
        'Director',
        'Officer',
        'President',
        'Vice',
        'Operations Officer',
        'Financial Officer',
        'Non-Independant Director',
        'Independant Director',
        
    ]
    
    for i in replacement_elements:
        s = s.replace(i, ' ^ ')
    
    return s
 

def fn_check_file_create(pathIN,age_threshold):
    
    threshold_check = datetime.now() - timedelta(days=age_threshold)
    
    try:
        
        fileCreation = os.path.getctime(pathIN)
        filetime = datetime.fromtimestamp(fileCreation)

        if filetime < threshold_check:
            st.write(f"File last update {filetime} is more than {age_threshold} days old.")
            renew_file = True 
        else:
            st.write(f"File last update {filetime} is less than {age_threshold} days old.")
            renew_file = False
    
    except:
        
        renew_file = True    
        st.write(f"File not found.")

    return renew_file 


def fn_print_message(message, duration):
    
    with st.sidebar:
        
        msg = st.empty()
    
        for i in range(duration):
                msg.success(message, icon=None)
        
        msg.empty()

def fn_format_board_table(dfIN):
    
    dfIN = dfIN[[
    "ticker_symbol",
    "board_member_name",
    "board_member_title",
    "board_member_profile",
    "last_updated",
    #"status",
    "board_member_url"]]
    
    dfIN['board_member_profile'] = dfIN['board_member_profile'].str.wrap(100)
    
    return dfIN

def fn_print_company_profiles(ticker_symbol,company_name, address1,address2, address3, phone, company_sector, industry, revenue, netincome, employees):
    
    company_string = f'{company_name} - ticker:{ticker_symbol} | Revenue:{revenue}'
    fn_print_sh(company_string ,'red')
    html_string = f'<div class="divTable">\
                        <div class="divTableBody">\
                            <div class="divTableRow">\
                                <div class="divTableCell">{address1}</div>\
                            </div> \
                            <div class="divTableRow">\
                                <div class="divTableCell">{address2}</div>\
                            </div> \
                            <div class="divTableRow">\
                                <div class="divTableCell">{address3}</div>\
                            </div> \
                            <div class="divTableRow">\
                                <div class="divTableCell">{phone}</div>\
                            </div> \
                            <div class="divTableRow">\
                                <div class="divTableCell">Sector:&nbsp;{company_sector} | Industry:&nbsp;{industry}</div>\
                            </div> \
                            <div class="divTableRow">\
                                <div class="divTableCell">Revenue:&nbsp;{revenue} | Net Income:&nbsp;{netincome} | Employees:&nbsp;{employees}</div>\
                            </div> \
                        </div>\
                    </div><hr>'
    st.markdown(html_string, unsafe_allow_html=True)


def fn_print_board_profiles(name,link, role,ticker, profile, lastupdated):
    
    html_string = f'<div class="divTable"> \
                    <div class="divTableBody"> \
                    <div class="divTableRow"> \
                    <div class="divTableCell"><h4><a href="{link}">{name}</a><br>{ticker} - {role}</h4>Profile Updated: &nbsp;{lastupdated}</div> \
                    </div> \
                    <div class="divTableRow"> \
                    <div class="divTableCell">{profile}</div> \
                    </div> \
                    </div>'
    st.markdown(html_string, unsafe_allow_html=True)
    
def fn_print_sh(s,color):
    st.subheader(f":{color}[{s}]")   
    
def fn_print_transcript_snippet(name,title, role,company_name,organization, call_date,discourse,score,label):
    
    discourse = discourse.replace("^","")
    
    if company_name == organization:
        organization = '' 
    
    fn_print_sh(role,'red')
    html_string = f'<div class="divTable">\
                    <div class="divTableBody">\
                    <div class="divTableRow">\
                    <div class="divTableCell">{name} - {title}</div>\
                    <div class="divTableCell">{company_name}</div>\
                    <div class="divTableCell">{organization}</div>\
                    </div>\
                    <div class="divTableRow">\
                    <div class="divTableCell">Date:&nbsp;{call_date} - finBERT label:&nbsp;{label} - Model score:&nbsp;{score}</div>\
                    </div>\
                    <div class="divTableRow">\
                    <div class="divTableCell"><br>{discourse}</div>\
                    </div>\
                    </div>\
                    </div><hr>'
    st.markdown(html_string, unsafe_allow_html=True)
    
 
def fn_refresh_data(path):
    
    if path == 'macro_urls.csv':
    
        df_urls = fn_return_urls()
        fn_print_message(f"{path} saved", 90)
        #df_urls.to_csv('macro_urls.csv', index=False)
        hs.to_s3('jm-ces-esg-summaries', df_urls, 'macro_urls.csv','CSV')
        return df_urls
    
    if path == 'macro_raw_tickers.csv':
    
        df_raw_tickers = fn_return_tickers()
        fn_print_message(f"{path} saved", 90)
        #df_raw_tickers.to_csv('macro_raw_tickers.csv', index=False)
        hs.to_s3('jm-ces-esg-summaries', df_raw_tickers, 'macro_raw_tickers.csv','CSV')
        return df_raw_tickers
    
    
    if path == 'esg_ticker_discourse.csv':
        
        '''
            Pull latest Athena transcript summary file of top ESG mentioning companies
            Then, join the ticker table and pull the latest company profile
            Then, create the summary profiles and the tree view
        '''
        
        # pull the latest transcript summary file
        st.write('pulling athena')
        df_esg_discourse = fn_return_athena_query()
        
        df_esg_discourse = df_esg_discourse#[df_esg_discourse['role']=='Executive']
        df_esg_discourse = df_esg_discourse.drop_duplicates(subset = ['discourse'],keep = 'last').reset_index(drop = True)
        df_esg_discourse.drop(columns=['transcript_unique_row_id'], inplace=True)
        df_esg_discourse.rename(columns={'discourse2':'transcript_unique_row_id'}, inplace=True)
        df_esg_discourse['discourse'] = df_esg_discourse.apply(lambda x: fn_replace_discourse_item(x['discourse']), axis=1 )
        
        st.write(df_esg_discourse)
        #df_esg_discourse.to_csv('esg_ticker_discourse.csv', index=False)
        hs.to_s3('jm-ces-esg-summaries', df_esg_discourse, 'esg_ticker_discourse.csv','CSV')
        
        fn_print_message(f"{path} saved", 20)
        return df_esg_discourse
    
    if path == 'esg_company_profiles.csv':
        
        '''
        Refresh ESG company profile information from DynamoDB process
        '''
        # pull latest dynamo db summary of ticker symbols
        df_tickers = fn_return_tickers()
        df_esg_discourse = pd.merge(df_esg_discourse,df_tickers, how='left', left_on='company', right_on=['ticker_symbol']  )
        
        #st.write(len(df_esg_discourse))
        
        key_cols = ["address1","address2","address3","address4",
        "phone","symbol","company_sector", "industry",
        "fiscal_year","revenue",
        "netincome","sales_growth","employees"]
        
        df_esg_pivot = pd.pivot_table(df_esg_discourse, index=['ticker_symbol'], values=['company'], aggfunc='count').reset_index()
        
        '''
        # Creates a subset where we only focus on companies that have had at least 5 high
        # probability utterances over a 2-3 year period
        '''
        
        df_esg_pivot = df_esg_pivot[df_esg_pivot['company']>=5]
        #st.write(len(df_esg_pivot))
        df_esg_pivot = df_esg_pivot.drop_duplicates(subset = ['ticker_symbol'])
        df_esg_pivot[key_cols] = df_esg_pivot.apply(lambda x: hs.fn_return_ticker_descriptors(x['ticker_symbol']), axis=1)
        #df_esg_pivot.to_csv('esg_company_profiles.csv', index=False)
        hs.to_s3('jm-ces-esg-summaries', existing_esg_df, 'esg_company_profiles.csv','CSV')
        fn_print_message(f"{path} saved", 20)
        return df_esg_pivot
    
    
    if path == 'esg_board_profiles.csv':
        
        df_board_profiles = pd.DataFrame()
        total_tickers = len(df_esg_pivot['ticker_symbol'])
        count = 0 
        my_bar = st.progress(0)   
        
        for x in df_esg_pivot['ticker_symbol']:
            
            try: 
                #existing_esg_df = pd.read_csv('esg_board_profiles.csv') 
                existing_esg_df = hs.fn_from_s3('esg_board_profiles.csv','jm-ces-esg-summaries')
                
                if existing_esg_df[existing_esg_df['ticker_symbol']==x]:
                    # add it back to the current dataframe
                    df_board_profiles = df_board_profiles.append(existing_esg_df[existing_esg_df['ticker_symbol']==x])
                    #skip and don't pull anything
                else:
                    msg_out=(f'Building board profile for {x} syymbol')  
                    fn_print_message(msg_out, 1)  
                    # returns a dataframe with the board of director profiles
                    df_temp = hs.fn_return_board(x)
                    existing_esg_df = existing_esg_df.append(df_temp)    
                    #existing_esg_df.to_csv('esg_board_profiles.csv',index=False)
                    hs.to_s3('jm-ces-esg-summaries', existing_esg_df, 'esg_board_profiles.csv','CSV')
                    
            except:
                msg_out=(f'Building board profile for {x} syymbol')  
                fn_print_message(msg_out, 1)   
                
                # returns a dataframe with the board of director profiles
                df_temp = hs.fn_return_board(x)
                df_board_profiles = df_board_profiles.append(df_temp)    
                #df_board_profiles.to_csv('esg_board_profiles.csv',index=False)
                hs.to_s3('jm-ces-esg-summaries', df_board_profiles, 'esg_board_profiles.csv','CSV')
        
        #pause so we freak out the marketwatch website.        
            time.sleep(1.5)
            percent_complete = str(round(count/total_tickers,2)*100) + "%"
            my_bar.progress(percent_complete + 1)
        
        return df_board_profiles   
    

def fn_get_data():
    
    # CurrentDate = datetime.datetime.now()
    # CurrentDate = datetime.datetime.strptime(str(CurrentDate), "%d/%m/%Y %H:%M")
    # st.write(f'Current Date {CurrentDate}')
    
    
    try:  
        
        df_raw_tickers = hs.fn_from_s3('macro_raw_tickers.csv','jm-ces-esg-summaries')
                
        df_urls = hs.fn_from_s3('macro_urls.csv','jm-ces-esg-summaries')
        
       # st.write(df_urls.columns.tolist())
    
        df_esg_discourse = hs.fn_from_s3('esg_ticker_discourse.csv','jm-ces-esg-summaries')
        df_esg_discourse = df_esg_discourse.drop_duplicates(subset = ['discourse'],keep = 'last').reset_index(drop = True)
        
        df_esg_pivot = hs.fn_from_s3('esg_company_profiles.csv','jm-ces-esg-summaries')
        
        df_board_profiles = hs.fn_from_s3('esg_board_profiles.csv','jm-ces-esg-summaries')
        
        df_board_profiles = fn_format_board_table(df_board_profiles)
        
        # st.write('df_esg_pivot')
        # st.write(df_esg_pivot.head(10))
        
        # st.write('df_esg_discourse')
        # st.write(df_esg_discourse.head(10))
        
        # st.write('df_board_profiles')
        # st.write(df_board_profiles.head(10))
        
        # st.write('df_urls')
        # st.write(df_urls.head(10))
        
        # st.write('df_raw_tickers')
        # st.write(df_raw_tickers.head(10))
        
        with st.sidebar:
            
            
            st.info('Available Data Successfully Loaded')

            if st.text_input(label='update', type='password') == 'streamlit': 
                if st.button('Update Transcript URLs Info (~30 sec)'):
                    df_urls = fn_refresh_data('macro_urls.csv')
                
                if st.button('Update List of Ticker Symbols (~30 sec)'):
                    df_raw_tickers = fn_refresh_data('macro_raw_tickers.csv')
                    
                if st.button('Update Company Profile Info (~30 sec)'):
                    df_esg_pivot = fn_refresh_data('esg_company_profiles.csv')
        
                if st.button('Update Board Profile Info (~15 min)'):
                    df_board_profiles = fn_refresh_data('esg_board_profiles.csv')
                    df_board_profiles = fn_format_board_table(df_board_profiles)
        
                if st.button('Update Transcript Data (~30 sec)'):
                    df_esg_discourse = fn_refresh_data('esg_ticker_discourse.csv')

            # TODO 
            # This in the controller/dataprocessing layer at some point happening in the background
            # versus on the fly in streamlit everytime. 
            df_esg_discourse = df_esg_discourse.merge(df_esg_pivot[['company_name','ticker_symbol','company_sector','industry']], left_on=['company'], right_on=['ticker_symbol'])
            df_board_profiles = df_board_profiles.merge(df_esg_pivot, how='left', on=['ticker_symbol'])
            #df_urls = df_urls.merge(df_esg_pivot, how='left', on=['ticker_symbol'])
            df_board_profiles = df_board_profiles.drop_duplicates(subset=['board_member_name','ticker_symbol'])
            df_esg_discourse = df_esg_discourse.drop_duplicates(subset=['discourse'])
            df_esg_discourse['year'] = pd.to_datetime(df_esg_discourse['call_date']).dt.year
            df_esg_discourse['month'] = pd.to_datetime(df_esg_discourse['call_date']).dt.month
            
            return df_esg_discourse, df_esg_pivot, df_board_profiles, df_urls, df_raw_tickers
   
    except Exception as e:                 
            st.warning(f'{e} here')
    

'''
VISUALIZATION SECTION HERE
'''

def fn_utterance_time_series_bar_chart(df_esg_discourse):
    
    t = pd.pivot_table(df_esg_discourse, index=['year','month'], columns=['role'], values=['label'], aggfunc='count').reset_index()
    t.columns = t.columns.droplevel(0)
    t.columns = ['year','month','analyst_count','executive_count']
    #t = t.sort_values(by=['year','month'],ascending=True)
    t = pd.melt( t,id_vars=['year','month'],value_vars=['analyst_count','executive_count'], ignore_index=True )
    t['year-mo'] = t['year'].astype(str) + "-" + t['month'].astype(str)
    
    chart = alt.Chart(t).mark_bar().encode(
        x='year-mo',
        y='sum(value)',
        color='variable'
    ).interactive()
    
    fn_print_sh("ESG Environmental-related Utterances on Investor Calls",'blue')    
    st.info('80%+ utterance confidence only. Analyst count refers to utterances associated with analyst q/a wheareas executive count correspond to executive statements')
    st.altair_chart(chart, use_container_width=True)
    

def fn_utterance_industry_bubble_chart(df_esg_discourse):
    
    #st.write(df_esg_discourse.sample(30))
    #df_esg_discourse = df_esg_discourse.apply(lambda x: 'Other' if x['company_sector']=='' else x['company_sector'])
    t = pd.pivot_table(df_esg_discourse, index=['industry'], columns=['company_sector'], values=['label'], aggfunc='count').reset_index()
    
    temp_company_sector_listing = t.iloc[0].reset_index()['company_sector'].tolist()
    temp_company_sector_listing = [i for i in temp_company_sector_listing if i]  #<-- remove blanks list elements
    t.columns = ['industry'] + temp_company_sector_listing
   # t.columns = t.columns.droplevel(0)
    
    t.fillna(0,inplace=True)
    t = pd.melt( t,id_vars=['industry'],value_vars=temp_company_sector_listing, ignore_index=True )
   # t['year-mo'] = t['year'].astype(str) + "-" + t['month'].astype(str)
    
    #st.write(t.head(3))
    
    chart = alt.Chart(t).mark_circle().encode(
    y=alt.Y('variable:N'),
    x='industry',
    size='sum(value):Q',
    order='value'
    ).interactive().properties(height=500)
    
    fn_print_sh("ESG Environmental-related Utterances by Sector & Industry (~2020-2022)",'blue')    
    st.info('80%+ utterance confidence only.')
    st.altair_chart(chart, use_container_width=True)
    
       
    
def fn_utterance_rank_barchart(url_df, company_df):
    
    url_df['company_ticker'] = url_df['ticker_symbol'] + " - " + url_df['company_name'] 
    url_piv = pd.pivot_table(url_df, index=['company_ticker','ticker_symbol'], values=['all_esg_mentions','environmental_mentions'], aggfunc={'all_esg_mentions':'sum', 'environmental_mentions':'sum'},margins=True).reset_index()

    url_piv = url_piv[url_piv['company_ticker']!='All']
    
    transcript_count = len(url_df)
    company_count = len(company_df)
    
    url_piv = url_piv.sort_values(by=['environmental_mentions'],ascending=False)
    
    url_piv.rename(columns={'environmental_mentions':'Env/Energy Utterance','all_esg_mentions':'Total ESG-related Utterances'},inplace=True)
    
    #st.write(url_piv)
    
    filter = 50     
    t = pd.melt(url_piv.head(filter),id_vars=['company_ticker'], value_vars=['Total ESG-related Utterances','Env/Energy Utterance'], ignore_index=True)
    
    #t = t.sort_values(by=['value'],ascending=False)
    #t = t.sort_values(by=['company_ticker','value'],ascending=[True,True]).reset_index()

    #st.write(t)
    
    chart = alt.Chart(t).mark_bar().encode(
        y=alt.Y('company_ticker', sort='-x'),
        x=alt.X('value:Q'),
        color='variable',
        order='value'
        # order=alt.Order(
        # # Sort the segments of the bars by this field
        # 'company_ticker',
        # sort='ascending'
        # )
    ).interactive().properties(height=800)
    
    fn_print_sh("2020-2022 Investory Call Transcript Review",'blue')
    st.write(f'Top {filter} Environmental Mention Frequency Companies')
    st.info(f"NLP finBERT ESG Analysis for Mention of ESG Terms ~{transcript_count} transcripts analyzed for {company_count} publicly listed companies over ~2020-2022 tune period." )
    st.altair_chart(chart, use_container_width=True)
    
  

# def fn_demo_tree_chart():
    
#     mention_details = {
#     'ESG Tree' : ['ESG Analysis', 'ESG Analysis', 'ESG Analysis', 'ESG Analysis', 'ESG Analysis', 'ESG Analysis','ESG Analysis'],
#     'Industry' : ['Food', 'Food', 'Energy', 'Energy', 'Energy', 'Energy','Airline'],
#     'ESG Mentions' : ['40', '40', '40', '40','10','10','5'],
#     'ticker_symbol' : ['ADM', 'ADM','NEE', 'NEE','AES', 'AES','AAL'],
#     'role' : ['CEO', 'President','CFO', 'Director', 'CEO', 'President','CEO'],
#     'speakers' : ['ADM_Speaker_1', 'ADM_Speaker_2','NEE_Speaker_1', 'NEE_Speaker_2', 'AES_Speaker1', 'AES_Speaker2','AAL_Speark3'],
#     #'speakers2' : ['ADM_Speaker_1', 'ADM_Speaker_2','NEE_Speaker_1', 'NEE_Speaker_2', 'AES_Speaker1', 'AES_Speaker2','AAL_Speark3'],
#     }

#     board_details = {
#         'ticker_symbol' : ['ADM', 'ADM','NEE', 'NEE','AES', 'AES','AES', 'AES','AAL','AAL','AAL'],
#         'board' : ['ADM Board 1', 'ADM Board 2','NEE Board 1', 'NEE Board 2','AES Board 1', 'AES Board 2','AES Board 3','AES Board 4','AAL Board 1', 'AAL Board 2','AAL Board 3'],
#     }
  
#     # creating a Dataframe object 
#     df_transcripts = pd.DataFrame(mention_details)
#     df_board = pd.DataFrame(board_details)   
    
#     df = df_transcripts 

#    # func5 = [{'name': name, 'values': []} for i, name in zip(df[df.columns[4]], df[df.columns[5]])]
#     #func4 = [{'name': name, 'children': []} for i, name in zip(df[df.columns[5]], df[df.columns[4]])]
    
#     func3 = [{'name': name, 'children': []} for i, name in zip(df[df.columns[1]], df[df.columns[2]])]

#     children = [{'name': name, 'children': [func3]} for i, name in zip(df[df.columns[0]], df[df.columns[1]])]
#     new_dict = {'name':'ESG Analysis', 'children': children}

#     st.write(new_dict)
#     return new_dict


# def render_basic_tree():
#     # with open("./data/flare.json", "r") as f:
#     #     data = json.loads(f.read())
#     #     st.write(type(data))
#     #     st.write(data)
#     dictIN = fn_demo_tree_chart()
#     data = dictIN

#     for idx, _ in enumerate(data["children"]):
#         data["children"][idx]["collapsed"] = idx % 2 == 0

#     option = {
#         "tooltip": {"trigger": "item", "triggerOn": "mousemove"},
#         "series": [
#             {
#                 "type": "tree",
#                 "data": [data],
#                 "top": "1%",
#                 "left": "7%",
#                 "bottom": "1%",
#                 "right": "20%",
#                 "symbolSize": 7,
#                 "label": {
#                     "position": "left",
#                     "verticalAlign": "middle",
#                     "align": "right",
#                     "fontSize": 9,
#                 },
#                 "leaves": {
#                     "label": {
#                         "position": "right",
#                         "verticalAlign": "middle",
#                         "align": "left",
#                     }
#                 },
#                 "emphasis": {"focus": "descendant"},
#                 "expandAndCollapse": True,
#                 "animationDuration": 550,
#                 "animationDurationUpdate": 750,
#             }
#         ],
#     }
#     st.write("hello")
#     st_echarts(option, height="500px")