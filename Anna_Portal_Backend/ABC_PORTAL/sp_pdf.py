import pyodbc
import os

port = '23'
host = '104.153.122.227'
database = 'S78F13CW'
user = 'onetgart'
password = 'abcpass21'


def map_network_drive(drive_letter, network_path, username, password):
    try:
        # Command to map the network drive
        command = f'net use {drive_letter} {network_path} {password} /user:{username}'
        os.system(command)
        print(f"Network drive {drive_letter} mapped successfully.")
    except Exception as e:
        print(f"Error mapping network drive: {e}")


def call_stored_procedure_pdf(ssn, ssn_path, ssn_file):

   
    drive_letter = 'V:'
    network_path = r'\\104.153.122.227\HOME\DURGA'
    map_network_drive(drive_letter, network_path, user, password)


    connection_string = (
        f"DRIVER={{iSeries Access ODBC Driver}};" 
        f"SYSTEM={host};"
        f"PORT={port};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        f"PROTOCOL=TCPIP;"
        f"CURRENTSCHEMA=QGPL;" 
    )

    param1 = ssn
    param2 = ssn_path
    param3 = ssn_file

    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        cursor.execute(
            "CALL QGPL.OOE_PROD_RUN_CL0164AS(?, ?, ?)", 
            (param1, param2, param3)
        )
        conn.commit()
        print("Stored procedure executed successfully.")
        return f"{drive_letter}\\{param3}"

    except pyodbc.Error as e:
        print(f"Error occurred: {e}")

    finally:
        if 'conn' in locals():
            cursor.close()
            conn.close()
print(call_stored_procedure_pdf('000007664', '/HOME/DURGA', '000007664.pdf'))