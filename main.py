from sap_conn import get_conn
from sap_rtab import rfc_read_table
from helper_files import chunks

import pandas as pd
import time


output_folder = "P:\Technisch\PLANY PRODUKCJI\PLANIŚCI\PP_TOOLS_TEMP_FILES\99_PyRFC_tests"

negative_bwarts = [
    '102',
]

materials = pd.read_excel("sap_nums.xlsx", header=0)
materials = materials['mat_nr'].astype(str).str.replace('.0', '', regex=False).str.strip().str.zfill(18).to_list()

storage_locations = ['0003', '0004', '0005']

mat_filter = " OR ".join(
    [f"MATNR = '{m}'" for m in materials]
)

stor_loc_filter = " OR ".join(
    [f"LGORT = '{loc}'" for loc in storage_locations]
)

date1 = '20260301'
date2 = '20260331'

start_time = time.time()

with get_conn("K11") as conn:
    attrs = conn.get_connection_attributes()
    print(attrs)
    print("SAP user:", attrs.get("user"))
    print("Client:", attrs.get("client"))
    print("System:", attrs.get("sysId"))

    mkpf = rfc_read_table(
        conn=conn,
        table="MKPF",
        fields=[
            "MBLNR",
            "MJAHR",
            "BUDAT",
        ],
        where=f"""
            BUDAT >= '{date1}'
            AND BUDAT <= '{date2}'
        """,
        # rowcount=150_000
    )

    mkpf_df = pd.DataFrame(mkpf)
    # print("MKPF DF: \n", mkpf_df.head(10))

    # Get list of MBLNR to use as a filter for mseg
    mkpf_keys = (
        mkpf_df[['MBLNR', 'MJAHR']]
        .drop_duplicates()
        .to_dict('records')
    )

    print("MKPF Execution Time: ", time.time() - start_time)

    mseg = []

    total_start = time.perf_counter()

    mkpf_chunks = list(chunks(mkpf_keys, 2000))
    material_chunks = list(chunks(materials, 4000))

    for mkpf_num, mkpf_chunk in enumerate(mkpf_chunks, start=1):

        is_printing = mkpf_num % 5 == 0

        mkpf_filter = " OR ".join(
            [
                f"(MBLNR = '{x['MBLNR']}' "
                f"AND MJAHR = '{x['MJAHR']}')"
                for x in mkpf_chunk
            ]
        )

        mkpf_start = time.perf_counter()

        if is_printing:
            print(
                f"\nMKPF chunk {mkpf_num}/{len(mkpf_chunks)} "
                f"| docs={len(mkpf_chunk)}"
            )

        for mat_num, mat_chunk in enumerate(material_chunks, start=1):
            mat_start = time.perf_counter()

            mat_filter = " OR ".join(
                [f"MATNR = '{m}'" for m in mat_chunk]
            )

            if is_printing:
                print(
                    f"  Material chunk "
                    f"{mat_num}/{len(material_chunks)} "
                    f"| mats={len(mat_chunk)}",
                    end=" -> "
                )

            mseg_chunk_data = rfc_read_table(
                conn=conn,
                table="MSEG",
                fields=[
                    "MBLNR",
                    "MJAHR",
                    "ZEILE",
                    "MATNR",
                    "WERKS",
                    "BWART",
                    "MENGE",
                    "LGORT",
                    "AUFNR"
                ],
                where=f"""
                    WERKS = '2101'
                    AND (
                        {stor_loc_filter}
                    )
                    AND (
                        BWART = '101'
                        OR BWART = '102'
                    )
                    AND (
                        {mat_filter}
                    )
                    AND (
                        {mkpf_filter}
                    )
                """
            )

            mseg.extend(mseg_chunk_data)

            mat_time = (
                    time.perf_counter()
                    - mat_start
            )

            if is_printing:
                print(
                    f"{len(mseg_chunk_data)} rows "
                    f"| {mat_time:.2f}s"
                )

        mkpf_time = (
                time.perf_counter()
                - mkpf_start
        )

        if is_printing:
            print(
                f"MKPF chunk {mkpf_num} "
                f"finished "
                f"({mkpf_time:.2f}s)"
            )

    total_time = (
            time.perf_counter()
            - total_start
    )

    print(
        f"\nFinished "
        f"| rows={len(mseg)} "
        f"| total={total_time:.2f}s"
    )

    mseg_df = pd.DataFrame(mseg)
    # print("MSEG DF: \n", mseg_df.head(10))


final_df = mseg_df.merge(
    mkpf_df,
    on=["MBLNR", "MJAHR"],
    how="left"
)

final_df["MENGE"] = final_df["MENGE"].astype(float)

final_df.loc[
    final_df['BWART'].isin(negative_bwarts),
    'MENGE'
] *= -1

final_df.to_excel(output_folder + "/final_df.xlsx", index=False)

print("Total_Execution Time: ", time.time() - start_time)
