import pyodbc
import logging
import pandas as pd

logging.basicConfig(level=logging.DEBUG)

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



# count = get_claims_count(f"01/13/2025")
# print(count)


def generate_claim_report(chssn_value,from_y,from_m,from_d,to_y,to_m,to_d):
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
        select_query = f"SELECT * FROM {schema_name}.{table_name} WHERE CHSSN = ? AND CHFRDY = ? AND CHFRDM = ? AND CHFRDD = ? AND CHTODM = ?  AND CHTODD = ? AND CHTODY = ?  "
        cursor.execute(select_query, (chssn_value,from_y,from_m,from_d,to_y,to_m,to_d,))

        # Fetch rows and get column names
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]  # Get column names
        df = pd.DataFrame.from_records(rows, columns=columns)  # Convert to DataFrame
        # Print the DataFrame
        ndf = df[["CHADPN", "CHDIAG", "CHDIA2", "CHDIA3", "CHDIA4", "CHDIA5",'CHCLM#','CHFRDY','CHFRDM','CHFRDD',"CHCLM$", "CHSTTY","CHCLTP",'CHPLAN','CHBNFT','CHMM$','CHCLD$','CHMEM$','CHCLEX','CHPATI','CHAMM$','CHRCDY','CHRCDM','CHRCDD','CHPRDM','CHPRDD','CHPRDY','CHEDI','CHHDST','CHPROV','CHTODM', 'CHTODD', 'CHTODY']]
        ndf['FROM DATE'] = ndf[['CHFRDM', 'CHFRDD', 'CHFRDY']].astype(str).agg('/'.join, axis=1)
        ndf['TO DATE'] = ndf[['CHTODM', 'CHTODD', 'CHTODY']].astype(str).agg('/'.join, axis=1)
        ndf['Receipt Date'] = ndf[['CHRCDM','CHRCDD','CHRCDY']].astype(str).agg('/'.join, axis=1)
        ndf['Processed Date'] = ndf[['CHPRDM','CHPRDD','CHPRDY']].astype(str).agg('/'.join, axis=1)
        ndf.drop(columns=['CHFRDM', 'CHFRDD', 'CHFRDY','CHPRDM','CHPRDD','CHPRDY','CHRCDM','CHRCDD','CHRCDY','CHTODM', 'CHTODD', 'CHTODY'],inplace=True)
        ndf.rename(columns={'CHCLM#':'CHCLM'},inplace=True)
        return ndf

    except Exception as e:
        print(f"Error: {e}")
        logging.error(e)
        return None

    finally:
        if connection:
            connection.close()
            print("Database connection closed.")


def check_credentials():
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

    schema_name = 'ooedf'
    table_name = 'empyp'

    try:
        connection = pyodbc.connect(connection_string)
        print("Connected to the database.")
        cursor = connection.cursor()

        # Query to get the total number of rows in the table
        count_query = f"SELECT COUNT(*) FROM {schema_name}.{table_name}"
        cursor.execute(count_query)
        total_rows = cursor.fetchone()[0]  # Get the total row count

        print(f"Total number of rows in the table: {total_rows}")

        # Query to get the first 10 rows of the table
        first_10_rows_query = f"SELECT * FROM {schema_name}.{table_name} FETCH FIRST 10 ROWS ONLY"
        cursor.execute(first_10_rows_query)

        # Fetch and print the first 10 rows
        rows = cursor.fetchall()
        print("First 10 rows in the table:")
        for row in rows:
            print(row)

    except Exception as e:
        print(f"Error: {e}")
        logging.error(e)

    finally:
        if connection:
            connection.close()
            print("Database connection closed.")

# check_credentials()



def get_class_name(key):
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
        print(df[['TBKEY', 'TBDESC']].drop_duplicates())
        current_select_query = f"SELECT * FROM ooedf.tablp WHERE TBCODE = 'CL' AND TBKEY ='{key}'"
        cursor.execute(current_select_query)
        current_row = cursor.fetchall()
        columns = [column[0] for column in cursor.description]  # Get column names
        current_df = pd.DataFrame.from_records(current_row, columns=columns) 
        current_class_name = list(current_df['TBDESC'])
        current_clas = current_class_name[0]
        class_name_list = list(df['TBDESC'])
        return class_name_list,current_clas
    except Exception as e:
        print("error",e)

def get_plan_name(key):
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
    try:
        connection = pyodbc.connect(connection_string)
        print("Connected to the database.")
        cursor = connection.cursor()

        # Execute SELECT query to fetch the first `n` rows
        select_query = f"SELECT * FROM ooedf.tablp WHERE TBCODE ='PL'"
        cursor.execute(select_query)

        # Fetch rows and get column names
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]  # Get column names
        df = pd.DataFrame.from_records(rows, columns=columns) 
        
        plan_name = list(df['TBDESC'])
        return plan_name
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
            return False
        elif chale_val < 0:
            return False
        else:
            return True
    except Exception as e:
        print("error",e)

def check_eligibility(ssn):
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

        select_query = "SELECT * FROM ooedf.elghp WHERE ELSSN = ?"
        cursor.execute(select_query,ssn)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        df = pd.DataFrame(rows, columns=columns)
        print(df)
    except Exception as e:
        print("ERROR",e)

# c = get_claims_count("12/30/2024")
# print(c)



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

# Example usage

# def db_check():
#     host = '10.68.4.201'
#     port = '23'
#     database = 'S06e6f1r'
#     user = 'ONEADMIN'
#     password = 'ONEADMIN'

#     connection_string = (
#         f"DRIVER={{iSeries Access ODBC Driver}};"
#         f"SYSTEM={host};"
#         f"PORT={port};"
#         f"DATABASE={database};"
#         f"UID={user};"
#         f"PWD={password};"
#         f"PROTOCOL=TCPIP;"
#     )

#     connection = pyodbc.connect(connection_string)
#     cursor = connection.cursor()
#     query = """
#     SELECT dpssn, COUNT(*) 
#     FROM OOEDF.DEPNP 
#     GROUP BY dpssn 
#     HAVING COUNT(*) > 1;
#     """
#     cursor.execute(query)
#     results = cursor.fetchall()
#     for row in results:
#         print(f"Duplicate dpssn: {row[0]}, Count: {row[1]}")
#     # for row in results:
#     #     print(f"Column Name: {row.COLUMN_NAME}, Constraint Name: {row.CONSTRAINT_NAME}")

#     print("done")

# db_check()
