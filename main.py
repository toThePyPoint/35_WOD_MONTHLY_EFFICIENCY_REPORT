from retriving_sap_data import get_mkpf_and_mseg_afpo_data
from send_email import send_email_from_application

import pandas as pd
from datetime import datetime
import time
import tkinter as tk
from tkinter import messagebox


SAP_SYSTEM = "P11_SSO"
# SAP_SYSTEM = "K11"


output_folder = r"P:\Technisch\PLANY PRODUKCJI\PLANIŚCI\PP_TOOLS_TEMP_FILES\16_WOD_MONTHLY_EFFICIENCY_REPORT\output"
master_data_folder = r"P:\Technisch\PLANY PRODUKCJI\PLANIŚCI\PP_TOOLS_TEMP_FILES\16_WOD_MONTHLY_EFFICIENCY_REPORT\master-data"
data_file_name = r'\RaportDane.xlsx'


def ask_for_report_dates():
    date_format = "%Y-%m-%d"
    default_date = datetime.today().strftime(date_format)
    result = {"date1": None, "date2": None}

    root = tk.Tk()
    root.title("Report dates")
    root.resizable(False, False)

    tk.Label(root, text="Start date (yyyy-mm-dd):").grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
    date1_entry = tk.Entry(root, width=16)
    date1_entry.insert(0, default_date)
    date1_entry.grid(row=0, column=1, padx=10, pady=(10, 5))

    tk.Label(root, text="End date (yyyy-mm-dd):").grid(row=1, column=0, padx=10, pady=5, sticky="w")
    date2_entry = tk.Entry(root, width=16)
    date2_entry.insert(0, default_date)
    date2_entry.grid(row=1, column=1, padx=10, pady=5)

    def submit():
        try:
            parsed_date1 = datetime.strptime(date1_entry.get().strip(), date_format)
            parsed_date2 = datetime.strptime(date2_entry.get().strip(), date_format)
        except ValueError:
            messagebox.showerror("Invalid date", "Please enter dates in yyyy-mm-dd format.", parent=root)
            return

        result["date1"] = parsed_date1.strftime("%Y%m%d")
        result["date2"] = parsed_date2.strftime("%Y%m%d")
        root.destroy()

    def cancel():
        root.destroy()

    button_frame = tk.Frame(root)
    button_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="e")
    tk.Button(button_frame, text="OK", width=10, command=submit).pack(side="left", padx=(0, 5))
    tk.Button(button_frame, text="Cancel", width=10, command=cancel).pack(side="left")

    root.bind("<Return>", lambda _event: submit())
    root.bind("<Escape>", lambda _event: cancel())
    date1_entry.focus_set()
    root.mainloop()

    if result["date1"] is None or result["date2"] is None:
        raise SystemExit("Report date selection cancelled.")

    return result["date1"], result["date2"]


date1, date2 = ask_for_report_dates()

negative_bwarts = [
    '102', '261'
]


def format_report_date(date_text):
    return datetime.strptime(date_text, "%Y%m%d").strftime("%Y-%m-%d")


def efficiency_report(prd_ord_df, data_df, master_data_folder, data_file, date_range):
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
    result_sheet_df['Szt'] = result_sheet_df['Szt'].astype(int)

    # total sum row
    total_sum = result_sheet_df["Szt"].sum()
    total_row = pd.DataFrame({result_sheet_df.columns[0]: ["RAZEM"], "Szt": [total_sum]})
    result_sheet_df = pd.concat([result_sheet_df, total_row], ignore_index=False)
    result_sheet_df.to_html('report.html')

    # Load the HTML content
    with open("report.html", "r", encoding='utf-8') as file:
        html_content = file.read()

    # date_today = datetime.today().strftime('%Y-%m-%d')

    email_body = f"Wydajność WOD {date_range}:\n" + html_content
    subject = f"Raport Wydajności {date_range}"
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

formatted_date1 = format_report_date(date1)
formatted_date2 = format_report_date(date2)

if formatted_date1 == formatted_date2:
    report_date_range = formatted_date1
else:
    report_date_range = f"{formatted_date1} - {formatted_date2}"

efficiency_report(final_df_101_102, data_df, master_data_folder, data_file_name, report_date_range)

print("Total_Execution Time: ", time.time() - start_time)
