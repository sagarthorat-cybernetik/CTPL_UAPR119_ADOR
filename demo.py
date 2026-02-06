import pyodbc

DB_CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.200.24,1433;"
    "DATABASE=ZONE03_REPORTS;"
    "UID=dbuserz03;"
    "PWD=CTPL@123"
)

conn = pyodbc.connect(DB_CONNECTION_STRING)
cursor = conn.cursor()

# Create table query 
"""
Date_Time	Serial_Number	Channel No.	Machine No.	TESTING TYPE	CH-Capacity(Ah)	CH-Pack Voltage(V)	CH-HCV	CH-Cell Deviation	CH-Temp	CH-Temp Deviation	DCH-Capacity(Ah)	DCH-Pack Voltage(V)	DCH-LCV	DCH-Cell Deviation	DCH-Temp	DCH-Temp Deviation	END SOC	STATUS	Step Timing	Cycle Time

"""
create_table_query = """
    CREATE TABLE IF NOT EXISTS  (
        Date_Time DATETIME,
        Serial_Number VARCHAR(255),
        Channel_No INT,
        Machine_No VARCHAR(255),
        Testing_Type VARCHAR(255),
        CH_Capacity_Ah REAL,
        CH_Pack_Voltage_V REAL,
        CH_HCV REAL,
        CH_Cell_Deviation REAL,
        CH_Temp REAL,
        CH_Temp_Deviation REAL,
        DCH_Capacity_Ah REAL,
        DCH_Pack_Voltage_V REAL,
        DCH_LCV REAL,
        DCH_Cell_Deviation REAL,
        DCH_Temp REAL,
        DCH_Temp_Deviation REAL,
        END_SOC REAL,
        STATUS BIT,
        Step_Timing INT,
        Cycle_Time INT
    );
"""
cursor.execute(create_table_query)
conn.commit()
conn.close()

# check if datatable is created or not and print the coloumns names
conn = pyodbc.connect(DB_CONNECTION_STRING)
cursor = conn.cursor()
cursor.execute("SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Battery_Test_Results'")
table_exists = cursor.fetchone()
if table_exists:
    print("Table 'Battery_Test_Results' exists.")
    cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Battery_Test_Results'")
    columns = cursor.fetchall()
    print("Columns in 'Battery_Test_Results':")
    for column in columns:
        print(column[0])
else:
    print("Table 'Battery_Test_Results' does not exist.")
cursor.close()
conn.close()
