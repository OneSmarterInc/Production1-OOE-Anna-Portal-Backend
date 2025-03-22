import pyodbc
import logging
import pandas as pd

# Enable logging
logging.basicConfig(level=logging.DEBUG)

# Database connection details
def get_bhpnam_by_claim(claim_number):
    host = '104.153.122.227'
    port = '23'
    database = 'S78F13CW'
    user = 'ONEPYTHON'
    password = 'pa33word'

    connection_string = (
        f"DRIVER={{iSeries Access ODBC Driver}};"
        f"SYSTEM={host};"
        f"PORT={port};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        f"PROTOCOL=TCPIP;"
    )
    try:
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # SQL Query with a WHERE condition
        sql_query = """
            SELECT 
                b.BHPNAM,
                b.BHCAMT    
            FROM ooedf.clmhp a              
            INNER JOIN ooedf.ediclhp b      
            ON a.CHCLM# = b.BHBCLN
            WHERE a.CHCLM# = ?
        """

        # Execute the query with parameter
        cursor.execute(sql_query, (claim_number,))
        row = cursor.fetchone()
        return (row[0], row[1]) if row else (None, None)

    except Exception as e:
        return {"error": str(e)}

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

def fetch_claims_data_for_clmp():
    host = '104.153.122.227'
    port = '23'
    database = 'S78F13CW'
    user = 'ONEPYTHON'
    password = 'pa33word'

    connection_string = (
        f"DRIVER={{iSeries Access ODBC Driver}};"
        f"SYSTEM={host};"
        f"PORT={port};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        f"PROTOCOL=TCPIP;"
    )

    # Table name and schema
    schema_name = 'OOEDF'
    table_name = 'CLMHP'
    try:
        connection = pyodbc.connect(connection_string)
        print("Connected to the database.")
        cursor = connection.cursor()

        # Execute SELECT query to fetch the first `n` rows
        select_query = f"SELECT * FROM {schema_name}.{table_name}"
        cursor.execute(select_query)

        # Fetch rows and get column names
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]  # Get column names
        df = pd.DataFrame.from_records(rows, columns=columns)  # Convert to DataFrame
        needed_df = df[['CHCLM#','CHPCLM','CHSSN','CHFRDY','CHFRDM','CHFRDD',"CHADPN", "CHCLM$", "CHPAY$", "CHMEM$", "CHSTTY","CHCLTP",'CHPROV']]
        needed_df['DATE'] = needed_df[['CHFRDM', 'CHFRDD', 'CHFRDY']].astype(str).agg('/'.join, axis=1)
        needed_df.drop(columns=['CHFRDM', 'CHFRDD', 'CHFRDY'],inplace=True)
        return needed_df

    except Exception as e:
        print(f"Error: {e}")
        logging.error(e)
        return None

    finally:
        if connection:
            connection.close()
            print("Database connection closed.")


def fetch_claims_data_for_dependent_using_ssn(chssn_value,seq_value):
    host = '104.153.122.227'
    port = '23'
    database = 'S78F13CW'
    user = 'ONEPYTHON'
    password = 'pa33word'

    connection_string = (
        f"DRIVER={{iSeries Access ODBC Driver}};"
        f"SYSTEM={host};"
        f"PORT={port};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        f"PROTOCOL=TCPIP;"
    )

    # Table name and schema
    schema_name = 'OOEDF'
    table_name = 'CLMHP'
    try:
        connection = pyodbc.connect(connection_string)
        print("Connected to the database.")
        cursor = connection.cursor()

        # Execute SELECT query to fetch the first `n` rows
        select_query = f"SELECT * FROM {schema_name}.{table_name} WHERE CHSSN = ? AND CHDEP# = ?"
        cursor.execute(select_query, (chssn_value,seq_value))

        # Fetch rows and get column names
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]  # Get column names
        df = pd.DataFrame.from_records(rows, columns=columns)  # Convert to DataFrame
        # Print the DataFrame
        ndf = df[["CHADPN", "CHDIAG", "CHDIA2", "CHDIA3", "CHDIA4", "CHDIA5",'CHCLM#','CHFRDY','CHFRDM','CHFRDD',"CHCLM$", "CHSTTY","CHCLTP",'CHPLAN','CHBNFT','CHMM$','CHCLD$','CHMEM$','CHCLEX','CHPATI','CHAMM$','CHRCDY','CHRCDM','CHRCDD','CHPRDM','CHPRDD','CHPRDY','CHEDI','CHHDST','CHPROV','CHTODM', 'CHTODD', 'CHTODY']]
        ndf['DATE'] = ndf[['CHFRDM', 'CHFRDD', 'CHFRDY']].astype(str).agg('/'.join, axis=1)
        ndf['Receipt Date'] = ndf[['CHRCDM','CHRCDD','CHRCDY']].astype(str).agg('/'.join, axis=1)
        ndf['Processed Date'] = ndf[['CHPRDM','CHPRDD','CHPRDY']].astype(str).agg('/'.join, axis=1)
        ndf['TO DATE'] = ndf[['CHTODM', 'CHTODD', 'CHTODY']].astype(str).agg('/'.join, axis=1)
        ndf.drop(columns=['CHFRDM', 'CHFRDD', 'CHFRDY','CHPRDM','CHPRDD','CHPRDY','CHRCDM','CHRCDD','CHRCDY','CHTODM', 'CHTODD', 'CHTODY'],inplace=True)
        ndf.rename(columns={'CHCLM#':'CHCLM'},inplace=True)
        ndf[['CHADPN', 'BHCAMT']] = ndf['CHCLM'].apply(lambda x: pd.Series(get_bhpnam_by_claim(x)))
        return ndf

    except Exception as e:
        print(f"Error: {e}")
        logging.error(e)
        return None

    finally:
        if connection:
            connection.close()
            print("Database connection closed.")

def fetch_claims_data_for_member_using_ssn(chssn_value):
    host = '104.153.122.227'
    port = '23'
    database = 'S78F13CW'
    user = 'ONEPYTHON'
    password = 'pa33word'

    connection_string = (
        f"DRIVER={{iSeries Access ODBC Driver}};"
        f"SYSTEM={host};"
        f"PORT={port};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        f"PROTOCOL=TCPIP;"
    )

    # Table name and schema
    schema_name = 'OOEDF'
    table_name = 'CLMHP'
    try:
        connection = pyodbc.connect(connection_string)
        print("Connected to the database.")
        cursor = connection.cursor()

        # Execute SELECT query to fetch the first `n` rows
        select_query = f"SELECT * FROM {schema_name}.{table_name} WHERE CHSSN = ? AND CHDEP# = ?"
        cursor.execute(select_query, (chssn_value,0.0))

        # Fetch rows and get column names
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]  # Get column names
        df = pd.DataFrame.from_records(rows, columns=columns)  # Convert to DataFrame
        # Print the DataFrame
        ndf = df[["CHADPN", "CHDIAG", "CHDIA2", "CHDIA3", "CHDIA4", "CHDIA5",'CHCLM#','CHFRDY','CHFRDM','CHFRDD',"CHCLM$", "CHSTTY","CHCLTP",'CHPLAN','CHBNFT','CHMM$','CHCLD$','CHMEM$','CHCLEX','CHPATI','CHAMM$','CHRCDY','CHRCDM','CHRCDD','CHPRDM','CHPRDD','CHPRDY','CHEDI','CHHDST','CHPROV','CHTODM', 'CHTODD', 'CHTODY']]
        ndf['DATE'] = ndf[['CHFRDM', 'CHFRDD', 'CHFRDY']].astype(str).agg('/'.join, axis=1)
        ndf['Receipt Date'] = ndf[['CHRCDM','CHRCDD','CHRCDY']].astype(str).agg('/'.join, axis=1)
        ndf['Processed Date'] = ndf[['CHPRDM','CHPRDD','CHPRDY']].astype(str).agg('/'.join, axis=1)
        ndf['TO DATE'] = ndf[['CHTODM', 'CHTODD', 'CHTODY']].astype(str).agg('/'.join, axis=1)
        ndf.drop(columns=['CHFRDM', 'CHFRDD', 'CHFRDY','CHPRDM','CHPRDD','CHPRDY','CHRCDM','CHRCDD','CHRCDY','CHTODM', 'CHTODD', 'CHTODY'],inplace=True)
        ndf.rename(columns={'CHCLM#':'CHCLM'},inplace=True)
        ndf[['CHADPN', 'BHCAMT']] = ndf['CHCLM'].apply(lambda x: pd.Series(get_bhpnam_by_claim(x)))
        return ndf

    except Exception as e:
        print(f"Error: {e}")
        logging.error(e)
        return None

    finally:
        if connection:
            connection.close()
            print("Database connection closed.")


def fetch_claims_data_using_claim_no(claim_number):
    host = '104.153.122.227'
    port = '23'
    database = 'S78F13CW'
    user = 'ONEPYTHON'
    password = 'pa33word'

    connection_string = (
        f"DRIVER={{iSeries Access ODBC Driver}};"
        f"SYSTEM={host};"
        f"PORT={port};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        f"PROTOCOL=TCPIP;"
    )

    # Table name and schema
    schema_name = 'OOEDF'
    table_name = 'CLMDP'
    try:
        connection = pyodbc.connect(connection_string)
        print("Connected to the database.")
        cursor = connection.cursor()

        # Execute SELECT query to fetch the first `n` rows
        select_query = f"SELECT * FROM {schema_name}.{table_name} WHERE CDCLM# = ?"
        cursor.execute(select_query, (claim_number,))
        # Fetch rows and get column names
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]  # Get column names
        df = pd.DataFrame.from_records(rows, columns=columns)  # Convert to DataFrame
        ndf = df[["CDCLM#","CDFRDY", "CDFRDM", "CDFRDD", "CDTODY", "CDTODM", "CDTODD", "CDBNCD", "CDAPTC", "CDCPT#", "CDCPTM", "CDCHG$", "CDNPC$", "CDPAY$","CDSRVP"]]
        ndf['FROM DATE'] = ndf[['CDFRDM', 'CDFRDD', 'CDFRDY']].astype(str).agg('/'.join, axis=1)
        ndf.drop(columns=['CDFRDM', 'CDFRDD', 'CDFRDY'],inplace=True)
        ndf['TO DATE'] = ndf[['CDTODM', 'CDTODD', 'CDTODY']].astype(str).agg('/'.join, axis=1)
        ndf.drop(columns=['CDTODM', 'CDTODD', 'CDTODY'],inplace=True)
        ndf.rename(columns={'CDCLM#':'CDCLM'},inplace=True)
        return ndf

    except Exception as e:
        print(f"Error: {e}")
        logging.error(e)
        return None

    finally:
        if connection:
            connection.close()
            print("Database connection closed.")


def get_claims_count(date_str):
    host = '104.153.122.227'
    port = '23'
    database = 'S78F13CW'
    user = 'ONEPYTHON'
    password = 'pa33word'

    connection_string = (
        f"DRIVER={{iSeries Access ODBC Driver}};"
        f"SYSTEM={host};"
        f"PORT={port};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        f"PROTOCOL=TCPIP;"
    )

    # Table name and schema
    schema_name = 'OOEDF'
    table_name = 'CLMHP'
    M, D, Y = date_str.split("/")
    print(M,D,Y)
    try:
        connection = pyodbc.connect(connection_string)
        print("Connected to the database.")
        cursor = connection.cursor()

        count_query = f"SELECT COUNT(*) FROM {schema_name}.{table_name} WHERE CHDTEY = ? AND CHDTEM = ? AND CHDTED = ?"

        cursor.execute(count_query, (Y, M, D))

        claim_count = cursor.fetchone()[0]
        return claim_count

    except Exception as e:
        print(f"Error: {e}")
        logging.error(e)
        return None

    finally:
        if connection:
            connection.close()
            print("Database connection closed.")



def generate_claim_report(chssn_value, from_date, to_date, claim_no=None):
    host = '104.153.122.227'
    port = '23'
    database = 'S78F13CW'
    user = 'ONEPYTHON'
    password = 'pa33word'

    connection_string = (
        f"DRIVER={{iSeries Access ODBC Driver}};"
        f"SYSTEM={host};"
        f"PORT={port};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        f"PROTOCOL=TCPIP;"
    )

    schema_name = 'OOEDF'
    table_name = 'CLMHP'

    try:
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        sql = f"""
        SELECT * FROM {schema_name}.{table_name}
        WHERE CHSSN = ? 
        AND TIMESTAMP_FORMAT(CHFRDM || '/' || LPAD(CHFRDD, 2, '0') || '/' || CHFRDY, 'MM/DD/YYYY') 
            BETWEEN TIMESTAMP_FORMAT(?, 'MM/DD/YYYY') AND TIMESTAMP_FORMAT(?, 'MM/DD/YYYY')
        AND TIMESTAMP_FORMAT(CHTODM || '/' || LPAD(CHTODD, 2, '0') || '/' || CHTODY, 'MM/DD/YYYY') 
            BETWEEN TIMESTAMP_FORMAT(?, 'MM/DD/YYYY') AND TIMESTAMP_FORMAT(?, 'MM/DD/YYYY')
        """

        params = [chssn_value, from_date, to_date, from_date, to_date]

        if claim_no:
            sql += " AND CHCLM# = ?"
            params.append(claim_no)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        df = pd.DataFrame.from_records(rows, columns=columns)

        if not df.empty:
            df["FROM DATE"] = df[['CHFRDM', 'CHFRDD', 'CHFRDY']].astype(str).agg('/'.join, axis=1)
            df["TO DATE"] = df[['CHTODM', 'CHTODD', 'CHTODY']].astype(str).agg('/'.join, axis=1)
            df["Receipt Date"] = df[['CHRCDM','CHRCDD','CHRCDY']].astype(str).agg('/'.join, axis=1)
            df["Processed Date"] = df[['CHPRDM','CHPRDD','CHPRDY']].astype(str).agg('/'.join, axis=1)
            df.drop(columns=['CHFRDM', 'CHFRDD', 'CHFRDY', 'CHPRDM', 'CHPRDD', 'CHPRDY', 
                             'CHRCDM', 'CHRCDD', 'CHRCDY', 'CHTODM', 'CHTODD', 'CHTODY'], inplace=True)
            df.rename(columns={'CHCLM#': 'CHCLM'}, inplace=True)
        
        return df

    except Exception as e:
        logging.error(e)
        return None

    finally:
        if connection:
            connection.close()

def get_class_name(key):
    host = '10.68.4.201'
    port = '23'
    database = 'S06e6f1r'
    user = 'ONEADMIN'
    password = 'ONEADMIN'


    connection_string = (
        f"DRIVER={{iSeries Access ODBC Driver}};"
        f"SYSTEM={host};"
        f"PORT={port};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        f"PROTOCOL=TCPIP;"
    )

    # Table name and schema
    try:
        connection = pyodbc.connect(connection_string)
        print("Connected to the database.")
        cursor = connection.cursor()

        # Execute SELECT query to fetch the first `n` rows
        select_query = f"SELECT * FROM ooedf.tablp WHERE TBCODE = 'CL'"
        cursor.execute(select_query)
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]  # Get column names
        df = pd.DataFrame.from_records(rows, columns=columns) 
        try:
            current_select_query = f"SELECT * FROM ooedf.tablp WHERE TBCODE = 'CL' AND TBKEY ='{key}'"
            cursor.execute(current_select_query)
            current_row = cursor.fetchall()
            columns = [column[0] for column in cursor.description]  # Get column names
            current_df = pd.DataFrame.from_records(current_row, columns=columns) 
            current_class_name = list(current_df['TBDESC'])
            current_clas = current_class_name[0]
        except:
            current_clas = ''
        class_name_list = list(df['TBDESC'])
        return class_name_list,current_clas
    except Exception as e:
        print("error",e)


def get_plan_name(key):
    host = '10.68.4.201'
    port = '23'
    database = 'S06e6f1r'
    user = 'ONEADMIN'
    password = 'ONEADMIN'


    connection_string = (
        f"DRIVER={{iSeries Access ODBC Driver}};"
        f"SYSTEM={host};"
        f"PORT={port};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        f"PROTOCOL=TCPIP;"
    )

    # Table name and schema
    try:
        connection = pyodbc.connect(connection_string)
        print("Connected to the database.")
        cursor = connection.cursor()

        # Execute SELECT query to fetch the first `n` rows
        select_query = f"SELECT * FROM ooedf.tablp WHERE TBCODE ='PL' AND TBKEY = '{key}'"
        cursor.execute(select_query)

        # Fetch rows and get column names
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]  # Get column names
        df = pd.DataFrame.from_records(rows, columns=columns) 
        plan_name = list(df['TBDESC'])
        return plan_name[0]
    except Exception as e:
        print("error",e)


def check_COB(ssn):
    host = '10.68.4.201'
    port = '23'
    database = 'S06e6f1r'
    user = 'ONEADMIN'
    password = 'ONEADMIN'


    connection_string = (
        f"DRIVER={{iSeries Access ODBC Driver}};"
        f"SYSTEM={host};"
        f"PORT={port};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        f"PROTOCOL=TCPIP;"
    )

    try:
        connection = pyodbc.connect(connection_string)
        print("Connected to the database.")
        cursor = connection.cursor()

        select_query = "SELECT CHALE$ FROM ooedf.clmhp WHERE CHSSN = ?"
        cursor.execute(select_query,ssn)

        row = cursor.fetchone()

        if row:
            chale_value = row[0]  
            print("CHALE$ Value:", chale_value)
        else:
            print("No record found.")
        chale_val = float(chale_value)
        if chale_val > 0:
            return "true"
        else:
            return "false"
    except Exception as e:
        return "not found for given ssn"