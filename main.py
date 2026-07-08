from retriving_sap_data import get_mkpf_and_mseg_afpo_data
from send_email import send_email_from_application

import pandas as pd
from datetime import datetime
import time


SAP_SYSTEM = "P11_SSO"
# SAP_SYSTEM = "K11"


output_folder = r"P:\Technisch\PLANY PRODUKCJI\PLANIŚCI\PP_TOOLS_TEMP_FILES\16_WOD_MONTHLY_EFFICIENCY_REPORT\output"
master_data_folder = r"P:\Technisch\PLANY PRODUKCJI\PLANIŚCI\PP_TOOLS_TEMP_FILES\16_WOD_MONTHLY_EFFICIENCY_REPORT\master-data"
data_file_name = r'\RaportDane.xlsx'

date1 = '20260707'
date2 = '20260707'

negative_bwarts = [
    '102', '261'
]

def efficiency_report(prd_ord_df, data_df, master_data_folder, data_file):
    """
    :param prd_ord_df: df with production orders data
    :return:
    """
    # cohv_df = pd.read_csv('cohv_df.csv', index_col="index")
    # cohv_df.drop(columns=['Unnamed: 0'], inplace=True)
    prd_ord_df["VERID"] = prd_ord_df["VERID"].replace('', pd.NA)
    prd_ord_df.fillna(value={"VERID": 0}, inplace=True)
    prd_ord_df = prd_ord_df.astype({"VERID": str})
    # prd_ord_df['VERID'] = prd_ord_df['VERID'].apply(lambda x: x.split(".")[0])

    # df with database
    # data_df = pd.read_excel(master_data_folder + data_file, sheet_name='BazaDanych', dtype={"WARIANT": str, 'SAP': str})
    # data_df['SAP'] = data_df['SAP'].str.strip().str.zfill(18)
    # data_df = data_df.astype({"WARIANT": str})

    merged_df = pd.merge(prd_ord_df, data_df, left_on=['MATNR', 'VERID'], right_on=['SAP', 'WARIANT']).reset_index()
    result_array = merged_df.groupby("TYP").sum()['MENGE']

    result_sheet_df = pd.read_excel(master_data_folder + data_file, sheet_name='ArkuszDanych', index_col='LP')
    result_sheet_df['Szt'] = result_sheet_df.index
    result_dict = result_array.to_dict()

    result_sheet_df['Szt'] = result_sheet_df['Szt'].apply(lambda x: result_dict.get(x, 0))

    # total sum row
    total_sum = result_sheet_df["Szt"].sum()
    total_row = pd.DataFrame({result_sheet_df.columns[0]: ["RAZEM"], "Szt": [total_sum]})
    result_sheet_df = pd.concat([result_sheet_df, total_row], ignore_index=False)
    result_sheet_df.to_html('report.html')

    # Load the HTML content
    with open("report.html", "r", encoding='utf-8') as file:
        html_content = file.read()

    date_today = datetime.today().strftime('%Y-%m-%d')

    email_body = f"Wydajność WOD {date_today}:\n" + html_content
    subject = f"Raport Wydajności {date_today}"
    recepients = ("dariusz.szumlak@rotofrank.com; robert.dobrzynski@rotofrank.com; grzegorz.fiutka@rotofrank.com;"
                  "arkadiusz.kubera@rotofrank.com;; marcin.wrobel@rotofrank.com; dariusz.dudek@rotofrank.com")

    send_email_from_application(recepients, subject, email_body)


start_time = time.time()

# materials = pd.read_excel("sap_nums.xlsx", header=0)
data_df = pd.read_excel(master_data_folder + data_file_name, sheet_name='BazaDanych', dtype={"WARIANT": str, 'SAP': str})
data_df['SAP'] = data_df['SAP'].str.strip().str.zfill(18)
# materials = pd.read_excel(master_data_folder + data_file_name, header=0)
materials = data_df['SAP'].drop_duplicates().tolist()

storage_locations = ['0003', '0004']

stor_loc_filter = " OR ".join(
    [f"LGORT = '{loc}'" for loc in storage_locations]
)

movement_types = ['101', '102']
movement_type_filter = " OR ".join(
    [f"BWART = '{type}'" for type in movement_types]
)

mkpf_df, mseg_df = get_mkpf_and_mseg_afpo_data(date1, date2, SAP_SYSTEM, stor_loc_filter, materials, movement_type_filter, 1000, 4000, 2000, 10)

final_df_101_102 = mseg_df.merge(
    mkpf_df,
    on=["MBLNR", "MJAHR"],
    how="left"
)

final_df_101_102["MENGE"] = final_df_101_102["MENGE"].astype(float)

# Ensure negative values for specified movement types
final_df_101_102.loc[
    final_df_101_102['BWART'].isin(negative_bwarts),
    'MENGE'
] *= -1

final_df_101_102.to_excel(output_folder + "/mseg_mkpf_101_102_df.xlsx", index=False)



# ===========================================================
# ============= 261 and 262 movement types ==================
# movement_types = ['261', '262']
# movement_type_filter = " OR ".join(
#     [f"BWART = '{type}'" for type in movement_types]
# )
#
# mkpf_df, mseg_df = get_mkpf_and_mseg_afpo_data(date1, date2, SAP_SYSTEM, stor_loc_filter, materials, movement_type_filter, 1000, 4000, 2000, 10)
#
# final_df = mseg_df.merge(
#     mkpf_df,
#     on=["MBLNR", "MJAHR"],
#     how="left"
# )
#
# final_df["MENGE"] = final_df["MENGE"].astype(float)
#
# # Ensure negative values for specified movement types
# final_df.loc[
#     final_df['BWART'].isin(negative_bwarts),
#     'MENGE'
# ] *= -1
#
# final_df.to_excel(output_folder + "/mseg_mkpf_261_262_df.xlsx", index=False)
# ===========================================================


efficiency_report(final_df_101_102, data_df, master_data_folder, data_file_name)

print("Total_Execution Time: ", time.time() - start_time)
