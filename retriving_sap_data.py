from sap_conn import get_conn
from sap_rtab import rfc_read_table
from helper_files import chunks

import pandas as pd

import time


def get_mkpf_and_mseg_afpo_data(date1, date2, sap_system, stor_loc_filter, materials, bwart_filter, mkpf_chunk_size, material_chunk_size, aufnr_chunks_size, printing_frequency):
    start_time = time.time()

    with get_conn(sap_system) as conn:
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

        mkpf_chunks = list(chunks(mkpf_keys, mkpf_chunk_size))
        material_chunks = list(chunks(materials, material_chunk_size))

        for mkpf_num, mkpf_chunk in enumerate(mkpf_chunks, start=1):

            is_printing = mkpf_num % printing_frequency == 0

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
                            {bwart_filter}
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
            f"\nFinished MSEG"
            f"| rows={len(mseg)} "
            f"| total={total_time:.2f}s"
        )

        mseg_df = pd.DataFrame(mseg)
        # print("MSEG DF: \n", mseg_df.head(10))

        afpo_start = time.perf_counter()

        customer_order_numers_list = mseg_df['AUFNR'].to_list()
        aufnr_chunks = chunks(customer_order_numers_list, aufnr_chunks_size)

        afpo = []

        for afpo_num, afpo_chunk in enumerate(aufnr_chunks, start=1):
            aufnr_start = time.perf_counter()
            is_printing = afpo_num % printing_frequency == 0

            aufnr_filter = " OR ".join(
                [f"AUFNR = '{num}'" for num in afpo_chunk]
            )

            afpo_chunk_data = rfc_read_table(
                conn=conn,
                table="AFPO",
                fields=["AUFNR", "VERID"],
                where=f"""
                    {aufnr_filter}
                """
            )

            afpo.extend(afpo_chunk_data)

            aufnr_time = (
                    time.perf_counter()
                    - aufnr_start
            )

            if is_printing:
                print(
                    f"{len(afpo_chunk)} rows "
                    f"| {aufnr_time:.2f}s"
                )

        total_time_afpo = (
                time.perf_counter()
                - afpo_start
        )

        print(
            f"\nFinished AFPO"
            f"| rows={len(afpo)} "
            f"| total={total_time_afpo:.2f}s"
        )

    afpo_df = pd.DataFrame(afpo)

    mseg_afpo_df = mseg_df.merge(afpo_df, how="left", on="AUFNR")

    return mkpf_df, mseg_afpo_df