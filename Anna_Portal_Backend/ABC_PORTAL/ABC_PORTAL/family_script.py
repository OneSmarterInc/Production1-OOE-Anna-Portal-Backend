import pandas as pd
import pyodbc
from tqdm import tqdm

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=ABCCOLUMBUSSQL2;'
    'DATABASE=EDIDATABASE;'
    'UID=sa;'
    'PWD=ChangeMe#2024;'
)
cursor = conn.cursor()

def get_existing_data(new_df):
    unique_ssns = "', '".join(new_df['ssn'].unique())
    query = f"""
        SELECT ssn, dep_ssn, sub_dep FROM famly_table 
        WHERE ssn IN ('{unique_ssns}')
    """
    return pd.read_sql(query, conn)

def insert_new_data(new_df, file_date):
    data = [
        (
            row['sub_dep'], row['first_name'], row['last_name'], row['ssn'], row['dep_ssn'],
            row['status'], row['type'], row['phone'], row['address1'], row['address2'],
            row['city'], row['state'], row['zip'], row['dob'], row['sex'], row['plan_edi'],
            row['class_field'], row['eff_date'], '', '', file_date, ''
        ) 
        for _, row in new_df.iterrows()
    ]

    batch_size = 1000  # Adjust batch size as needed
    total_batches = (len(data) + batch_size - 1) // batch_size

    with tqdm(total=len(data), desc="Inserting records", unit="rows") as pbar:
        for i in range(0, len(data), batch_size):
            batch = data[i:i+batch_size]
            cursor.executemany("""
                INSERT INTO famly_table (
                    sub_dep, first_name, last_name, ssn, dep_ssn, status, type, phone, 
                    address1, address2, city, state, zip, dob, sex, plan_edi, 
                    class_field, eff_date, term_date, remark, file_date, updated_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            conn.commit()
            pbar.update(len(batch))

    print("Insertion complete ✅")

def check_family_changes(existing_df, new_df):
    existing_subscribers = existing_df[existing_df['sub_dep'] == 'Subscriber']
    existing_dependents = existing_df[existing_df['sub_dep'] != 'Subscriber']
    new_subscribers = new_df[new_df['sub_dep'] == 'Subscriber']
    new_dependents = new_df[new_df['sub_dep'] != 'Subscriber']

    existing_ssn_map = existing_dependents.groupby('ssn')['dep_ssn'].apply(set).to_dict()
    new_ssn_map = new_dependents.groupby('ssn')['dep_ssn'].apply(set).to_dict()

    remarks = []

    for ssn, existing_deps in existing_ssn_map.items():
        new_deps = new_ssn_map.get(ssn, set())
        removed_deps = existing_deps - new_deps
        added_deps = new_deps - existing_deps

        for dep_ssn in removed_deps:
            remarks.append({'ssn': ssn, 'dep_ssn': dep_ssn, 'remark': "Dependent is no longer associated with this subscriber."})
        
        for dep_ssn in added_deps:
            remarks.append({'ssn': ssn, 'dep_ssn': dep_ssn, 'remark': "This dependent was newly added to the subscriber."})

    moved_dependents = []
    for dep_ssn in new_dependents['dep_ssn'].unique():
        old_ssn = existing_dependents.loc[existing_dependents['dep_ssn'] == dep_ssn, 'ssn']
        new_ssn = new_dependents.loc[new_dependents['dep_ssn'] == dep_ssn, 'ssn']

        if not old_ssn.empty and not new_ssn.empty and old_ssn.iloc[0] != new_ssn.iloc[0]:
            moved_dependents.append({
                'dep_ssn': dep_ssn, 'old_ssn': old_ssn.iloc[0], 'new_ssn': new_ssn.iloc[0],
                'remark': f"This dependent was earlier with {old_ssn.iloc[0]}, now with {new_ssn.iloc[0]}."
            })

    new_subscribers_only = new_subscribers[~new_subscribers['ssn'].isin(existing_subscribers['ssn'])]
    new_dependents_with_new_subs = new_dependents[new_dependents['ssn'].isin(new_subscribers_only['ssn'])]

    for _, row in new_dependents_with_new_subs.iterrows():
        remarks.append({
            'ssn': row['ssn'], 'dep_ssn': row['dep_ssn'], 
            'remark': "This dependent is associated with a newly added subscriber."
        })

    remarks_df = pd.DataFrame(remarks + moved_dependents)
    return remarks_df

def update_remarks(remarks_df,file_date):
    for _, row in remarks_df.iterrows():
        cursor.execute("""
            UPDATE famly_table
            SET remark = ?,updated_date = ?
            WHERE ssn = ? AND dep_ssn = ?
        """, row['remark'], file_date, row['ssn'], row['dep_ssn'])
    
    conn.commit()

def send_data_to_family_table(new_df,file_date):

    existing_df = get_existing_data(new_df)
    remarks_df = check_family_changes(existing_df, new_df)
    update_remarks(remarks_df,file_date)
    existing_ssns = existing_df['ssn'].unique()
    new_entries = new_df[~new_df['ssn'].isin(existing_ssns)]
    insert_new_data(new_entries,file_date)

    cursor.close()
    conn.close()