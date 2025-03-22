import pandas as pd
import pyodbc

# Database connection setup
from tqdm import tqdm
import csv
import os
import pyodbc
import smtplib
import pandas as pd,re
import random,string
import json
from datetime import datetime, timedelta
import time
import shutil
from multiprocessing import Queue
import pickle
from email.mime.text import MIMEText
import openpyxl
from openpyxl import Workbook
from email.mime.multipart import MIMEMultipart 
from email.mime.application import MIMEApplication
import sqlite3
from datetime import datetime
from email.mime.base import MIMEBase
from email import encoders
from io import BytesIO


csv_headers = [
    "SUB/DEP", "LAST NAME", "FIRST NAME", "SSN","TEMP SSN","SEX", "DOB", "DEP LAST NAME", "DEP FIRST NAME",
    "DEP SSN", "DEP SEX", "DEP DOB","CUSTODIAL PARENT","LOCAL", "plan_edi", "CLASS", "EFF DATE", "TERM DATE", "ID",
    "ADDRESS 1", "ADDRESS 2", "CITY", "STATE", "ZIP", "PHONE", "EMAIL", "STATUS", "TYPE","MEMBER ID","DEP ADDRESS","DEP CITY","DEP STATE","DEP ZIP"
]


def parse_edi_to_csv_for_sql_server_custodial(input_file_path):
    file_name = input_file_path.split("/")[-1]
    match = re.search(r'(\d{4})(\d{2})(\d{2})', file_name)
    if match:
        year, month, day = match.groups()
        formatted_date = f"{month}/{day}/{year}"
        print(formatted_date)
    else:
        formatted_date = 'NA'  # Extracts 'EDI_834_11-15-2024_3KXST5r.X12'
    #date_part = file_name.split("_")[2]
    #print("Extracted Date:", date_part)
    #date_part = str(date_part[:10])
    date_part='NA'
    with open(input_file_path, 'r') as file:
        edi_data = file.read()
    segments = edi_data.strip().split("~")
    csv_data = []
    current_subscriber = {}
    dependents = []
    error_logs = {}
    segment_list = []
    parsed_data_list = []
    total_parsed_data = []
    cus_data_list = []
    k = 0
    def extract_segment_data(segment, delimiter="*"):
        return segment.split(delimiter)

    for segment in segments:
        each_segments = segment.split("*") 
        segment_name = each_segments[0]  
        parsed_data = {}
        if segment_name in ["ISA", "GS", "ST", "BGN", "DTP", "N1", "INS", "REF", "NM1", 
                            "PER", "N3", "N4", "DMG", "HD", "SE", "GE", "IEA"]:
            parsed_data[segment_name] = "*".join(each_segments[1:])
            parsed_data_list.append(parsed_data)
            if segment_name == "HD":
                total_parsed_data.append({k:parsed_data_list})
                k += 1
                parsed_data_list = []
        else:
            print(f"Skipping unknown segment: {segment_name}")
        
        elements = extract_segment_data(segment)
        segment_id = elements[0]
        if segment_id not in segment_list:
            segment_list.append(segment_id)
        if segment_id == "REF":
            member_id_code = elements[1]
            if(member_id_code == "0F"):
                member_id = elements[2]
        if segment_id == "INS":
            relationship_code = elements[2]
            if relationship_code == '18':
                Sub = "Subscriber"
                Type = '18'
            else:
                dependent_type = elements[2]
                if dependent_type == '01':
                    Sub = "Spouse"
                    Type= dependent_type
                elif dependent_type == '19':
                    Sub = "Child"
                    Type = dependent_type
                else:
                    Sub = "Dependent"
                    Type= dependent_type
            if elements[1] == 'Y':
                status = 'Active'
            elif elements[1] == 'N':
                status = 'Inactive'
            else:
                status = ''

        elif segment_id == "NM1" and elements[1] == "IL":
            if current_subscriber:
                csv_data.append(current_subscriber)
                current_subscriber = {}
            sss = elements[-1] if len(elements) > 8 else ""
            sss = sss.replace("-", "").strip()
            if len(sss) == 9:
                sss = f"{sss[:3]}-{sss[3:5]}-{sss[5:]}"
            elif len(sss) == 8:
                sss = f"{sss[:2]}-{sss[2:4]}-{sss[4:]}"
            else:
                sss = "" 
            person = {
                "LAST NAME": elements[3] if len(elements) > 3 else "",
                "FIRST NAME": elements[4] if len(elements) > 4 else "",
                "SSN": sss,
                "SUB/DEP": Sub,
                "STATUS":status,
                "TYPE":Type,
                "MEMBER ID": member_id
            }
            current_subscriber.update(person)

        elif segment_id == "DMG" and len(elements) > 2:
            dob = elements[2]
            person = dependents[-1] if dependents else current_subscriber
            person["DOB"] = f"{dob[4:6]}/{dob[6:]}/{dob[:4]}" if len(dob) == 8 else ""
            person["SEX"] = elements[3] if len(elements) > 3 else ""
        
        elif "REF*17" in segment:
            data = segment.split("*")
            cus_data = data[-1]
            person["CUSTODIAL PARENT"] = cus_data

        elif segment_id == "N3" and len(elements) > 1:
            address = elements[1]
            person = dependents[-1] if dependents else current_subscriber
            person["ADDRESS 1"] = address

        elif segment_id == "N4" and len(elements) > 3:
            city, state, zip_code = elements[1:4]
            zerocode = zip_code.zfill(5)
            zip_code = str(zip_code).strip()
            if len(zip_code) < 5:
                zip_code = zip_code.zfill(5)
            elif len(zip_code) > 5:
                zip_code = zip_code[:5] 
            person = dependents[-1] if dependents else current_subscriber
            person.update({"CITY": city, "STATE": state, "ZIP": str(zip_code)})
        elif segment_id == "PER" and len(elements) > 3:
            phone = elements[-1]
            person = dependents[-1] if dependents else current_subscriber
            person["PHONE"] = phone

        elif segment_id == "HD" and len(elements) > 2:
            current_subscriber["plan_edi"] = elements[1]
            current_subscriber["CLASS"] = elements[3] if len(elements) > 3 else ""

        elif segment_id == "DTP" and len(elements) > 2:
            if elements[1] == "348":
                eff_date = elements[-1]
                current_subscriber["EFF DATE"] = f"{eff_date[4:6]}/{eff_date[6:]}/{eff_date[:4]}" if len(eff_date) == 8 else ""
            elif elements[1] == "349":
                term_date = elements[-1]
                current_subscriber["TERM DATE"] = f"{term_date[:4]}/{term_date[4:6]}/{term_date[6:]}" if len(term_date) == 8 else ""

        elif segment_id == "REF" and len(elements) > 2 and elements[1] == "1L":
            current_subscriber["ID"] = elements[2]
            if elements[2] == "L11958M001":
                current_subscriber["plan_edi"] = str("01")
                current_subscriber["CLASS"] = "01"
            
            elif elements[2] == "L11958M002":
                current_subscriber["plan_edi"] = str("01")
                current_subscriber["CLASS"] = "02"
                
            elif elements[2] == "L11958MD01":
                current_subscriber["plan_edi"] = "01"
                current_subscriber["CLASS"] = "SS"
                
            elif elements[2] == "L11958MR01":
                current_subscriber["plan_edi"] = "01"
                current_subscriber["CLASS"] = "R8"
                
            elif elements[2] == "L11958MR02":
                current_subscriber["plan_edi"] = "01"
                current_subscriber["CLASS"] = "D9"
                
            elif elements[2] == "L11958MR03":
                current_subscriber["plan_edi"] = "01"
                current_subscriber["CLASS"] = "R1"    
                
            elif elements[2] == "L11958MR04":
                current_subscriber["plan_edi"] = "01"
                current_subscriber["CLASS"] = "D2"       
                
            elif elements[2] == "L11958MR05":
                current_subscriber["plan_edi"] = "01"
                current_subscriber["CLASS"] = "M8"             
                
            elif elements[2] == "L11958MR06":
                current_subscriber["plan_edi"] = "01"
                current_subscriber["CLASS"] = "M9"    
                
            elif elements[2] == "L11958MR07":
                current_subscriber["plan_edi"] = "01"
                current_subscriber["CLASS"] = "M1"
                
            elif elements[2] == "L11958MR08":
                current_subscriber["plan_edi"] = "01"
                current_subscriber["CLASS"] = "M2"   
                
            elif elements[2] == "L11958MR09":
                current_subscriber["plan_edi"] = "01"
                current_subscriber["CLASS"] = "D0"     
                
            else:
                current_subscriber["plan_edi"] = "01"
                current_subscriber["CLASS"] = "01"

                error_logs[member_id] = elements[2]   
    errorFileName =  os.path.basename(input_file_path)
    # print(errorFileName)
    # if(len(error_logs) >0):
    #     error_message = "Missing group numbers for the given Member IDs"
    #     email = ['krishnarajjadhav2003@gmail.com']
    #     send_error_log_email(email, errorFileName, error_message, error_logs) 

    conn = sqlite3.connect("db.sqlite3")
    cursor = conn.cursor()
    import pandas as pd
    flattened_data = []
    flattened_data = []
    for group in total_parsed_data:
        for group_id, records in group.items():
            for record in records:
                for key, value in record.items():
                    flattened_data.append({'group_id': group_id, 'key': key, 'value': value})

    df = pd.DataFrame(flattened_data)
    df = df.groupby(['group_id', 'key'], as_index=False).agg({'value': 'first'})

    pivot_df = df.pivot(index='group_id', columns='key', values='value').reset_index()
    pivot_df = pivot_df.where(pd.notnull(pivot_df), None)
    pivot_df.drop(columns=['group_id'],inplace=True)
    for column in pivot_df.columns:
        pivot_df[column] = pivot_df[column].str.replace('*', '  ', regex=False)
        pivot_df[column] = pivot_df[column].drop_duplicates().reset_index(drop=True)
    pivot_df = pivot_df.fillna(' ')
    pivot_df['Date_edi'] = date_part
    random_number = random.randint(0, 9999)
    random_alphabet = random.choice(string.ascii_uppercase) 
    result = f"{random_alphabet}{random_number:04}"
    out_dir = "media/csv_files/"
    pivot_df_data = pivot_df.to_dict(orient="records")
    conn.close()
    csv_data.append(current_subscriber)
    csv_data.extend(dependents)
    input_filename = os.path.splitext(os.path.basename(input_file_path))[0]
    output_csv_path = 'C:'
    output_xlsx_path = os.path.join(out_dir, f"{input_filename}.xlsx")
    system_csv_path = 'C:'
    for row in csv_data:
        if 'ID' in row.keys():
            row['STATUS'] = row['ID']
        else:
            row['STATUS'] = ''
        if 'TYPE' in row.keys():
            row['ID'] = row['TYPE']
        else:
            row['ID'] = ''
        row['TYPE'] = ''
        if 'SSN' in row.keys():
            row['TEMP SSN'] = row['SSN']
        else:
            row['TEMP SSN'] = ''

    for path in [output_csv_path, system_csv_path]:
      
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Sheet1"
        worksheet.append(csv_headers)
        current_subscriber_ssn = None
        subscriber_address = None
        subscriber_city = None
        subscriber_zip = None
        subscriber_state = None
        previous_custodial_parent = None
        for row in csv_data:
            row["plan_edi"] = row["plan_edi"].zfill(2)
            row["CLASS"] = row["CLASS"].zfill(2)
            for key in row.keys():
                row[key] = str(row[key]) if row[key] is not None else ""

            if 'SUB/DEP' in row.keys():
                if row['SUB/DEP'] != 'Subscriber':
                    row['DEP FIRST NAME'] = str(row.get('FIRST NAME', "")).ljust(20)
                    row['DEP LAST NAME'] = str(row.get('LAST NAME', "")).ljust(20)
                    row['DEP DOB'] = str(row.get('DOB', "")).ljust(20)
                    row['DEP SSN'] = str(row.get('TEMP SSN', "")).ljust(20)
                    row['DEP SEX'] = str(row.get('SEX', "")).ljust(20)

            if 'SEX' in row.keys():
                if row['SEX'] == 'M' and row['SUB/DEP'] == 'Child':
                    row['SUB/DEP'] = 'SON'.ljust(20)
                elif row['SEX'] == 'F' and row['SUB/DEP'] == 'Child':
                    row['SUB/DEP'] = 'DAUGHTER'.ljust(20)
            if 'SUB/DEP' in row.keys():
                if row['SUB/DEP'] == 'Dependent':
                    row['SUB/DEP'] = 'OTHER'.ljust(20)

                if row["SUB/DEP"] == "Subscriber":
                    current_subscriber_ssn = row["SSN"]
                else:
                    row["SSN"] = current_subscriber_ssn
                if row["SUB/DEP"] == "Subscriber":
                    if "ADDRESS 1" in row and row["ADDRESS 1"]:
                        subscriber_address = row["ADDRESS 1"]
                    if 'ZIP' in row.keys() and 'CITY' in row.keys() and 'STATE' in row.keys():
                        subscriber_zip = row["ZIP"]
                        subscriber_city = row["CITY"]
                        subscriber_state = row["STATE"]
                else:
                    if "ADDRESS 1" in row and row["ADDRESS 1"]:
                        if row["ADDRESS 1"] != subscriber_address:
                            row["DEP ADDRESS"] = row["ADDRESS 1"]
                            row["ADDRESS 1"] = subscriber_address
                    if 'ZIP' in row.keys():    
                        if row["ZIP"] != subscriber_zip:
                                row["DEP ZIP"] = row["ZIP"]
                                row["ZIP"] = subscriber_zip
                    if 'CITY' in row.keys():
                        if row["CITY"] != subscriber_city:
                                row["DEP CITY"] = row["CITY"]
                                row["CITY"] = subscriber_city
                    if 'STATE' in row.keys():    
                        if row["STATE"] != subscriber_state:
                                row["DEP STATE"] = row["STATE"]
                                row["STATE"] = subscriber_state                            

            worksheet.append([row.get(header, "") for header in csv_headers])
        

    mssql_conn = pyodbc.connect(
            'DRIVER={ODBC Driver 17 for SQL Server};'
            'SERVER=ABCCOLUMBUSSQL2;'
            'DATABASE=EDIDATABASE;'
            'UID=sa;'
            'PWD=ChangeMe#2024;'
        )
    mssql_cursor = mssql_conn.cursor()
    cus_df = parse_custodial_data(csv_data)
    cus_df['EFF DATE'] = pd.to_datetime(cus_df['EFF DATE'])
    cus_df['EFF DATE'] = cus_df['EFF DATE'].apply(
    lambda x: '01/01/2025' if (pd.notna(x) and x < datetime(2025, 1, 1)) 
    else (x.strftime('%m/%d/%Y') if pd.notna(x) else 'NaT'))
    try:
        custodial_parent_df = cus_df[(cus_df['CUSTODIAL PARENT'].notna()) & (cus_df['CUSTODIAL PARENT'].str.strip() != "")]
        column_mapping = {
        'SUB/DEP': 'sub_dep',
        'LAST NAME': 'last_name',
        'FIRST NAME': 'first_name',
        'SSN': 'ssn',
        'SEX': 'sex',
        'DOB': 'dob',
        'DEP LAST NAME': 'dep_last_name',
        'DEP FIRST NAME': 'dep_first_name',
        'DEP SSN': 'dep_ssn',
        'DEP SEX': 'dep_sex',
        'DEP DOB': 'dep_dob',
        'LOCAL': 'address1',
        'plan_edi': 'plan_edi',
        'CLASS': 'class_field',
        'EFF DATE': 'eff_date',
        'TERM DATE': 'term_date',
        'ID': 'id_field',
        'ADDRESS 1': 'address1',
        'ADDRESS2': 'address2',
        'CITY': 'city',
        'STATE': 'state',
        'ZIP': 'zip',
        'PHONE': 'phone',
        'EMAIL': 'email',  
        'STATUS': 'status',
        'TYPE': 'type',
        'MEMBER ID': 'member_id',
        'CUSTODIAL PARENT': 'custodial_parent',
        'CUSTODIAL ADDRESS 1': 'custodial_address1',
        'CUSTODIAL ADDRESS 2': 'custodial_address2',
        'CUSTODIAL CITY': 'custodial_city',
        'CUSTODIAL STATE': 'custodial_state',
        'CUSTODIAL ZIP': 'custodial_zip',
        'CUSTODIAL PHONE': 'custodial_phone',
        'TEMP SSN': 'temp_ssn'
    }
        custodial_parent_df.rename(columns=column_mapping, inplace=True)
        custodial_parent_df['term_date'] = ''
        custodial_parent_df['filename'] = file_name
        custodial_parent_df['date_edi'] = formatted_date
        custodial_parent_df['address2'] = ''
        custodial_parent_df = custodial_parent_df[[
        "last_name", "first_name", "ssn", "sub_dep", "status", "type", "phone", "address1", "city", "state", "zip", "dob", "sex", 
        "plan_edi", "class_field", "eff_date", "id_field", "dep_first_name", "dep_last_name", "dep_dob", "dep_ssn", "dep_sex", 
        "custodial_parent", "custodial_address1", "custodial_address2", "custodial_city", "custodial_state", 
        "custodial_zip", "custodial_phone", "address2", "member_id", "date_edi", "filename", "temp_ssn", "term_date"]]
        temp_ssns = tuple(custodial_parent_df["temp_ssn"].unique())

        query = f"SELECT temp_ssn FROM myapp_custodial_data_table WHERE temp_ssn IN ({','.join(['?'] * len(temp_ssns))})"
        mssql_cursor.execute(query, temp_ssns)
        existing_temp_ssns = {row[0] for row in mssql_cursor.fetchall()}

        new_records_df = custodial_parent_df[~custodial_parent_df["temp_ssn"].isin(existing_temp_ssns)]
        new_records_data = new_records_df.to_dict(orient="records")
        print(new_records_data)
        try:
            if new_records_data:
                    insert_query = """
                    INSERT INTO myapp_custodial_data_table 
                    (last_name, first_name, ssn, sub_dep, status, type, phone, address1, city, state, zip, dob, sex, 
                    plan_edi, class_field, eff_date, id_field, dep_first_name, dep_last_name, dep_dob, dep_ssn, dep_sex, 
                    custodial_parent, custodial_address1, custodial_address2, custodial_city, custodial_state, 
                    custodial_zip, custodial_phone, address2, member_id, date_edi, filename, temp_ssn, term_date) 
                    VALUES 
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    
                    with mssql_conn:
                        mssql_cursor.executemany(insert_query, [tuple(d.values()) for d in new_records_data])
        except Exception as e:
            print("error cus", e)
    except Exception as e:
        print("error",e)


def parse_custodial_data(csv_data):
    new_df = pd.DataFrame(csv_data)
    new_df['CUSTODIAL ADDRESS 1'] = ''
    new_df['CUSTODIAL ADDRESS 2'] = ''
    new_df['CUSTODIAL CITY'] = ''
    new_df['CUSTODIAL STATE'] = ''
    new_df['CUSTODIAL ZIP'] = ''
    new_df['CUSTODIAL PHONE'] = ''
    if 'ID' in new_df.columns:
        new_df['ID'] = pd.to_numeric(new_df['ID'], errors='coerce')
        condition = new_df['ID'] == 15
    else:
        new_df['id_field'] = pd.to_numeric(new_df['id_field'], errors='coerce')
        condition = new_df['id_field'] == 15
    new_df.fillna('', inplace=True)

    if 'ADDRESS 1' in new_df.columns:
        new_df.loc[condition, 'CUSTODIAL ADDRESS 1'] = new_df.loc[condition, 'ADDRESS 1']
    elif 'address1' in new_df.columns:
        new_df.loc[condition, 'custodial_address_1'] = new_df.loc[condition,'address1']
    if 'ADDRESS 2' in new_df.columns:
        new_df.loc[condition, 'CUSTODIAL ADDRESS 2'] = new_df.loc[condition, 'ADDRESS 2']
    elif 'address2' in new_df.columns:
        new_df.loc[condition, 'custodial_address_2'] = new_df.loc[condition,'address2']
    if 'CITY' in new_df.columns:
        new_df.loc[condition, 'CUSTODIAL CITY'] = new_df.loc[condition, 'CITY']
    elif 'city' in new_df.columns:
        new_df.loc[condition, 'custodial_city'] = new_df.loc[condition,'city']
    if 'STATE' in new_df.columns:
        new_df.loc[condition, 'CUSTODIAL STATE'] = new_df.loc[condition, 'STATE']
    elif 'state' in new_df.columns:
        new_df.loc[condition, 'custodial_state'] = new_df.loc[condition,'state']
    if 'ZIP' in new_df.columns:
        new_df.loc[condition, 'CUSTODIAL ZIP'] = new_df.loc[condition, 'ZIP']
    elif 'zip' in new_df.columns:
        new_df.loc[condition, 'custodial_zip'] = new_df.loc[condition,'zip']
    if 'PHONE' in new_df.columns:
        new_df.loc[condition, 'CUSTODIAL PHONE'] = new_df.loc[condition, 'PHONE']
    elif 'phone' in new_df.columns:
        new_df.loc[condition, 'custodial_phone'] = new_df.loc[condition,'phone']
    
    sdf = new_df
    sdf_data = sdf.to_dict(orient="records")
    previous_custodial_parent = None
    custodial_parent_column = [row.get("CUSTODIAL PARENT", None) for row in sdf_data]
    shifted_custodial_parent_column = [None] + custodial_parent_column[:-1]

    for row, shifted_value in zip(sdf_data, shifted_custodial_parent_column):
        row["CUSTODIAL PARENT"] = shifted_value

    for row in sdf_data:
        if row["SUB/DEP"] != "Subscriber":
                if not row.get("CUSTODIAL ADDRESS 1") or row.get("DEP ADDRESS"):
                        if row.get("DEP ADDRESS"):
                            row["CUSTODIAL ADDRESS 1"] = row["DEP ADDRESS"]
                        elif row.get("ADDRESS 1"):
                            row["CUSTODIAL ADDRESS 1"] = row["ADDRESS 1"]
                if not row.get("CUSTODIAL ZIP") or row.get("DEP ZIP"):
                        if row.get("DEP ZIP"):
                            row["CUSTODIAL ZIP"] = row["DEP ZIP"]
                        elif row.get("ZIP"):
                            row["CUSTODIAL ZIP"] = row["ZIP"]


                if not row.get("CUSTODIAL CITY") or row.get("DEP CITY"): 
                        if row.get("DEP CITY"):
                            row["CUSTODIAL CITY"] = row["DEP CITY"]
                        elif row.get("CITY"):
                            row["CUSTODIAL CITY"] = row["CITY"]


                if not row.get("CUSTODIAL STATE"):
                        if row.get("DEP STATE"):
                            row["CUSTODIAL STATE"] = row["DEP STATE"]
                        elif row.get("STATE"):
                            row["CUSTODIAL STATE"] = row["STATE"]

    sdf = pd.DataFrame(sdf_data)
    desired_order = [
        "SUB/DEP", "LAST NAME", "FIRST NAME", "SSN", "TEMP SSN", "SEX", "DOB",
        "DEP LAST NAME", "DEP FIRST NAME", "DEP SSN", "DEP SEX", "DEP DOB",
        "CUSTODIAL PARENT", "LOCAL", "PLAN", "CLASS", "EFF DATE", "TERM DATE",
        "ID", "ADDRESS 1", "ADDRESS 2", "CITY", "STATE", "ZIP", "PHONE", 
        "EMAIL", "STATUS", "TYPE", "MEMBER ID"
    ]

    existing_columns = sdf.columns.tolist()
    columns_in_order = [col for col in desired_order if col in existing_columns]
    other_columns = [col for col in existing_columns if col not in desired_order]


    final_column_order = columns_in_order + other_columns

    sdf = sdf[final_column_order]
    sdf.drop(columns=['DEP ADDRESS','DEP ZIP','DEP STATE','DEP CITY'],inplace=True)
    return sdf

