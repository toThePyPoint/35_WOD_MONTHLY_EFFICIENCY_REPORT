from retriving_sap_data import get_mkpf_and_mseg_afpo_data

import pandas as pd
import time


SAP_SYSTEM = "P11_SSO"
# SAP_SYSTEM = "K11"


output_folder = r"P:\Technisch\PLANY PRODUKCJI\PLANIŚCI\PP_TOOLS_TEMP_FILES\16_WOD_MONTHLY_EFFICIENCY_REPORT"
date1 = '20260529'
date2 = '20260529'

negative_bwarts = [
    '102', '261'
]

start_time = time.time()

materials = pd.read_excel("sap_nums.xlsx", header=0)
materials = materials['mat_nr'].astype(str).str.replace('.0', '', regex=False).str.strip().str.zfill(18).to_list()

storage_locations = ['0003', '0004']

stor_loc_filter = " OR ".join(
    [f"LGORT = '{loc}'" for loc in storage_locations]
)

movement_types = ['101', '102']
movement_type_filter = " OR ".join(
    [f"BWART = '{type}'" for type in movement_types]
)

mkpf_df, mseg_df = get_mkpf_and_mseg_afpo_data(date1, date2, SAP_SYSTEM, stor_loc_filter, materials, movement_type_filter, 1000, 4000, 2000, 10)

final_df = mseg_df.merge(
    mkpf_df,
    on=["MBLNR", "MJAHR"],
    how="left"
)

final_df["MENGE"] = final_df["MENGE"].astype(float)

# Ensure negative values for specified movement types
final_df.loc[
    final_df['BWART'].isin(negative_bwarts),
    'MENGE'
] *= -1

final_df.to_excel(output_folder + "/mseg_mkpf_101_102_df.xlsx", index=False)

movement_types = ['261', '262']
movement_type_filter = " OR ".join(
    [f"BWART = '{type}'" for type in movement_types]
)

mkpf_df, mseg_df = get_mkpf_and_mseg_afpo_data(date1, date2, SAP_SYSTEM, stor_loc_filter, materials, movement_type_filter, 1000, 4000, 2000, 10)

final_df = mseg_df.merge(
    mkpf_df,
    on=["MBLNR", "MJAHR"],
    how="left"
)

final_df["MENGE"] = final_df["MENGE"].astype(float)

# Ensure negative values for specified movement types
final_df.loc[
    final_df['BWART'].isin(negative_bwarts),
    'MENGE'
] *= -1

final_df.to_excel(output_folder + "/mseg_mkpf_261_262_df.xlsx", index=False)

print("Total_Execution Time: ", time.time() - start_time)
