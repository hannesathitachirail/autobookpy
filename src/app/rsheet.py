from itertools import groupby
from re import split

import ezdxf as ez
import pandas as pd
import copy
import numpy as np
from pathlib import Path
import time
from pprint import pprint


pd.set_option("display.max_rows", None)


#############################################################################
# This class is used to create an Rsection object that takes the spreadsheet
# and creates one big dataframe(not split) containing all the rows that would
# be needed for the seperate Rsheets object
#
# The final output would be a list of sheets(dataframes) split into 40 row
# dataframes. This is used to create the Rsheet objects for every sheet(dataframes)
#############################################################################
class RSection:
    def __init__(self, excel_file, sheet):
        self.MAX_ROWS = 40
        self.dataframe = pd.read_excel(excel_file, sheet_name=["Border", "D", "E", "F"])
        ################ RACK sections #############
        self.idf_signal = IDFSignalsSheet(
            self.dataframe["D"], self.bordervalues, sheet
        )  # To be updated
        self.idf_points = IDFPointsSheet(
            self.dataframe["E"], self.bordervalues, self.idf_signal.next_sheet
        )  # To be updated
        self.op_signal = OPSignalsSheet(
            self.dataframe["D"], self.bordervalues, self.idf_points.next_sheet
        )
        self.op_point = OPPointsSheet(
            self.dataframe["E"], self.bordervalues, self.op_signal.next_sheet
        )  # To be updated
        self.op_counter = OPCountersSheet(
            self.dataframe["F"], self.bordervalues, self.op_point.next_sheet
        )  # To be updated
        ####################### CABINET Section #####################
        self.power = PowerRackSheet(
            self.dataframe["D"], self.bordervalues, self.op_counter.next_sheet
        )
        self.io = IORackSheet(
            self.dataframe["D"], self.bordervalues, self.power.next_sheet
        )
        self.points = PointsRackSheet(
            self.dataframe["E"], self.bordervalues, self.io.next_sheet
        )
        self.signals = SignalsRackSheet(
            self.dataframe["D"], self.bordervalues, self.points.next_sheet
        )
        self.strip = StripRackSheet(
            self.dataframe, self.bordervalues, self.signals.next_sheet
        )
        ##################### Axle Cabinet Section ####################
        self.axlecabinet = AxleCabinetSheet(
            self.dataframe["F"], self.bordervalues, self.strip.next_sheet
        )
        self.fadc = AxleFADCSheet(
            self.dataframe["F"], self.bordervalues, self.axlecabinet.next_sheet
        )
        self.axlestrip = StripAxleSheet(
            self.dataframe["F"], self.bordervalues, self.fadc.next_sheet
        )
        self.lstrip = AxleLSheet(
            self.dataframe["F"], self.bordervalues, self.axlestrip.next_sheet
        )
        self.mstrip = AxleMSheet(
            self.dataframe["F"], self.bordervalues, self.lstrip.next_sheet
        )

    @property
    def bordervalues(self):
        rows = self.dataframe["Border"].to_dict("records")
        row = rows[0]
        columns = {
            "BORDER_STATION_L1": f"{row['Station']} {row['Room']}"
            if row["Room"] != "nan"
            else f"{row['Station']}",
            "BORDER_STATION_L2": f"({row['Sta']} {row['Room']})"
            if row["Room"] != "nan"
            else f"({row['Sta']})",
            "BORDER_NAME": "**PLACEHOLDER**",
            "BORDER_SHEET": "R00",
            "BORDER_CSE": row["CSE"],
            "BORDER_STATION_CODE": row["Code"],
            "BORDER_DATE": row["Date"],
            "BORDER_DOC_NAME": row["Doc"],
            "DocDate": row["DocDate"],
            "BORDER_REV": row["Rev"],
        }
        return columns


######################################
# First sheet/sheets of Rsection, showing front of rack containing all the columns
######################################
class MountingSheet:
    def __init__(self):
        pass


###################
# Signals IDF sheets.
# Max 5 per sheet, max 10 per column (2 sheets).
# Reseved Column A and B
###################
class IDFSignalsSheet:
    def __init__(self, dataframe, bordervalues, sheet):
        self.MAX = 14
        self.MAX_PER_SHEET = 5  # Max individual IDF's per sheet
        self.dataframe = dataframe
        self.bordervalues = bordervalues
        self.sheet = sheet
        self.df = self.build_df()
        self.df_split = self.split_df()
        self.blocks = self.build_blocks()
        self.next_sheet = self.sheet

    def build_df(self):
        functiondict = {
            "G": ("DG", "DGCX"),
            "H": ("HG", "HGCX"),
            "R": ("RG", "RGCX"),
            "l": ("(L)UG", "(L)UGCX"),
            "s": ("(↑)UG", "(↑)UGCX"),
            "r": ("(R)UG", "(R)UGCX"),
        }
        tables: list[pd.DataFrame] = []
        for _, row in self.dataframe.fillna("").iterrows():
            table = pd.DataFrame(
                index=range(8),
                data={
                    "ROW": "A",
                    "POS": range(1, 9),
                    "INPUT TERMINAL": [f"{i}-" for i in range(1, 9)],
                    "FUNCTION": "SPARE",
                    "TYPE": "110 COPA 8 SURGE PROTECTION",
                    "OUTPUT TERMINAL": range(1, 9),
                    "SHEET": "-",
                },
            )
            if len(row["Aspect"] + row["Dir"]) <= 4:
                dir = str(row["Dir"].lower() if pd.notna(row["Dir"]) else "")
                table1_characters = row["Aspect"] + dir
                table1_function = []
                for character in table1_characters:
                    table1_function.extend(
                        [
                            f"{row['SignalName'][:-1]}{functiondict[character][0]}",
                            f"{row['SignalName'][:-1]}{functiondict[character][1]}",
                        ]
                    )
                table.loc[range(len(table1_function)), "FUNCTION"] = table1_function
                table.loc[range(len(table1_function)), "SHEET"] = row["Sheet"]
                tables.append(table)
            else:
                # Split into characters for table 1 and table2
                table1 = table.copy()
                table2 = table.copy()
                table1_characters = row["Aspect"]
                table2_characters = str(
                    row["Dir"].lower() if pd.notna(row["Dir"]) else ""
                )
                table1_function = []
                for character in table1_characters:
                    table1_function.extend(
                        [
                            f"{row['SignalName'][:-1]}{functiondict[character][0]}",
                            f"{row['SignalName'][:-1]}{functiondict[character][1]}",
                        ]
                    )
                table2_function = []
                for character in table2_characters:
                    table2_function.extend(
                        [
                            f"{row['SignalName'][:-1]}{functiondict[character][0]}",
                            f"{row['SignalName'][:-1]}{functiondict[character][1]}",
                        ]
                    )
                table1.loc[range(len(table1_function)), "FUNCTION"] = table1_function
                table2.loc[range(len(table2_function)), "FUNCTION"] = table2_function
                table1.loc[range(len(table1_function)), "SHEET"] = row["Sheet"]
                table2.loc[range(len(table2_function)), "SHEET"] = row["Sheet"]
                tables.append(table1)
                tables.append(table2)
        df = pd.concat(tables, ignore_index=True)
        df["POS"] = df.index // 8 + 1
        return df

    def split_df(self):
        dfs = [group for _, group in self.df.groupby(["POS"], sort=False, dropna=False)]
        # If rows exceed max allowed go to next column(B) and restart POS numbering
        # using df[whatever] is possible because dataframes are mutable objects
        for df in dfs:
            if df["POS"].iloc[0] > self.MAX:
                df["ROW"] = "B"
                df["POS"] = df["POS"] - self.MAX
        index = 0
        while index + 1 < len(dfs):
            df_current = dfs[index]
            df_next = dfs[index + 1]
            if (
                len(df_current) + len(df_next) <= self.MAX_PER_SHEET * 8
                and df_current["ROW"].iloc[0] == df_next["ROW"].iloc[0]
            ):
                dfs[index] = pd.concat([df_current, df_next])
                dfs.pop(index + 1)
            else:
                index += 1
        return dfs

    def build_blocks(self):
        # Iterate through list to isolate dataframe to a sheet
        blocks = []
        for sheetindex, dataframe in enumerate(self.df_split, start=1):
            blockdatalist = []
            self.bordervalues["BORDER_SHEET"] = f"R{self.sheet:03d}"
            blockdatalist.append(["PSP_BORDER_BLOCK", (0, 0), self.bordervalues.copy()])
            self.sheet += 1
            blockdatalist.append(
                [
                    "IDF_BASE",
                    (0, 0),
                    {
                        "TABLE_HEAD": f"IDF 11 - {dataframe['ROW'].iloc[0]}",
                    },
                ]
            )
            blockdatalist.append(
                [
                    "BORDER_INDEX_NAME",
                    (0, 0),
                    {
                        "BORDER_INDEX_NAME": f"IDF 11 - {dataframe['ROW'].iloc[0]} STRIP ANALYSIS ({sheetindex} OF {len(self.df_split)})"
                    },
                ]
            )

            dfs = [group for _, group in dataframe.groupby(["POS"])]
            for i, df in enumerate(dfs):
                blockdatalist.append(
                    [
                        "IDFSIG_TABLE",
                        (0, 0 - 40 * i),
                        {
                            "A1": df["ROW"].iloc[0],
                            "A2": df["POS"].iloc[0],
                            **{
                                f"A{e}": f"{df['FUNCTION'].iloc[e - 3]}"
                                for e in range(3, 11)
                            },
                            **{
                                f"A{e}": f"{df['SHEET'].iloc[e - 11]}"
                                for e in range(11, 19)
                            },
                        },
                    ]
                )
            blocks.append(blockdatalist)
        return blocks


#######################
# Points IDF sheets
# Max 10 per sheet, max
# Reserved Column C
#######################
class IDFPointsSheet:
    def __init__(self, dataframe, bordervalues, sheet):
        self.MAX = 14
        self.MAX_PER_SHEET = 5
        self.dataframe = dataframe
        self.bordervalues = bordervalues
        self.sheet = sheet
        self.df_split = self.split_df()
        self.blocks = self.build_blocks()
        self.next_sheet = self.sheet

    def split_df(self):
        df_split = [
            group
            for _, group in self.dataframe.groupby(
                self.dataframe.index // self.MAX_PER_SHEET
            )
        ]
        return df_split

    def build_blocks(self):
        # Iterate through list to isolate dataframe to a sheet
        blocks = []
        for sheetindex, dataframe in enumerate(self.df_split, start=1):
            blockdatalist = []
            self.bordervalues["BORDER_SHEET"] = f"R{self.sheet:03d}"
            blockdatalist.append(["PSP_BORDER_BLOCK", (0, 0), self.bordervalues.copy()])
            self.sheet += 1
            blockdatalist.append(
                [
                    "IDF_BASE",
                    (0, 0),
                    {
                        "TABLE_HEAD": f"IDF 11 - {dataframe['IDFRow'].iloc[0][0]}",
                    },
                ]
            )
            blockdatalist.append(
                [
                    "BORDER_INDEX_NAME",
                    (0, 0),
                    {
                        "BORDER_INDEX_NAME": f"IDF 11 - {dataframe['IDFRow'].iloc[0][0]} STRIP ANALYSIS ({sheetindex} OF {len(self.df_split)})"
                    },
                ]
            )
            for i, (_, row) in enumerate(dataframe.iterrows()):
                blockdatalist.append(
                    [
                        "IDFPOINT_TABLE",
                        (0, 0 - 40 * i),
                        {
                            "A1_1": row["IDFRow"][0],
                            "A1_2": row["IDFRow"][0],
                            "A2_1": row["IDFRow"][1:],
                            "A2_2": int(row["IDFRow"][1:]) + 1,
                            **{
                                f"A3_{e}": f"{row['PointName']} - W{e}"
                                for e in range(1, 5)
                            },
                            **{
                                f"A3_{e}": f"{row['PointName']} - W{e - 4}"
                                for e in range(5, 9)
                            },
                            **{f"A4_{e}": row["Sheet"] for e in range(1, 9)},
                        },
                    ]
                )
            blocks.append(blockdatalist)
        return blocks


#########################
# Signals OP sheets
# Max 40 terminals per sheet
########################
class OPSignalsSheet:
    def __init__(self, dataframe, bordervalues, sheet):
        self.MAX_ROWS = 40
        self.dataframe = dataframe
        self.bordervalues = bordervalues
        self.sheet = sheet
        self.df = self.build_df()
        self.df_split = self.split_df()
        self.blocks = self.build_blocks()
        self.next_sheet = self.sheet
        self.op_numbers = self.df.groupby("SHEET").min()["POS"]

    # Split the self.opdf into serperate dataframes consisting of the data
    # for every R sheet
    # Groups by CableAppCase and CableBox to form list of split dataframes
    # Because 1 cable(appcasecable usually) can be big enough to occupy
    # different sheets
    # To fix this we split the cable again into 40 lines max
    def build_df(self):
        # Start by reordering the dataframe.
        # Create list of dataframes grouped by "CableAppCase" and sorted by "AppCaseOrder"
        # for appcases group and "CableBox" for straight fed
        # pd.concat is used to merge the list of dataframes into one dataframe
        dfs = [
            group.sort_values("AppCaseOrder")
            if not pd.isna(group["CableAppCase"].iloc[0])
            else group.sort_values(
                "CableBox",
                key=lambda x: x.str.split(".").str[-1].astype(int).astype(int),
            )
            for _, group in self.dataframe.groupby("CableAppCase", dropna=False)
        ]

        # From the sorted dataframe we create another list of dataframes for every row
        # in dfs, the dataframe should have headers "ROW | POS | FUNCTION | TYPE | CABLE NAME | SHEET"
        functiondict = {
            "G": ("DG", "DGCX"),
            "H": ("HG", "HGCX"),
            "R": ("RG", "RGCX"),
            "l": ("(L)UG", "(L)UGCX"),
            "s": ("(↑)UG", "(↑)UGCX"),
            "r": ("(R)UG", "(R)UGCX"),
        }
        tables: list[pd.DataFrame] = []
        for df in dfs:
            if pd.notna(df["CableAppCaseQ"].iloc[0]):  # If Appcase
                cablename = df["CableAppCase"].iloc[0]
                cablesize = int(df["CableAppCaseQ"].iloc[0][:-2])
                terminals = cablesize * 2
                corelist = []
                for i in range(cablesize):
                    corelist.append(f"{i + 1}a")
                    corelist.append(f"{i + 1}b")
                table = pd.DataFrame(
                    index=range(terminals),
                    data={
                        "ROW": "D",
                        "POS": range(1, terminals + 1),
                        "FUNCTION": "SPARE",
                        "TYPE": "TERMINAL",
                        "CABLE NAME": cablename,
                        "CABLE PAIR": df["CableAppCaseQ"].iloc[0],
                        "CABLE DEST": df["CableAppCase"].iloc[0][-7:-2],
                        "CORE": corelist,
                        "SHEET": "-",
                    },
                )
                last_row = 0
                for _, row in df.iterrows():
                    dir = str(row["Dir"].lower() if pd.notna(row["Dir"]) else "")
                    characters = row["Aspect"] + dir
                    function = []
                    for character in characters:
                        function.extend(
                            [
                                f"{row['SignalName'][:-1]}{functiondict[character][0]}",
                                f"{row['SignalName'][:-1]}{functiondict[character][1]}",
                            ]
                        )
                    row_count = len(function)
                    indexes = range(last_row, last_row + row_count)
                    table.loc[indexes, "FUNCTION"] = function
                    table.loc[indexes, "TYPE"] = "TERMINAL"
                    table.loc[indexes, "SHEET"] = row["Sheet"]
                    last_row += row_count
                tables.append(table)
            else:
                for _, row in df.iterrows():
                    last_row = 0
                    cablename = row["CableBox"]
                    cablesize = int(row["CableBoxQ"][:-2])
                    terminals = cablesize * 2
                    corelist = []
                    for i in range(cablesize):
                        corelist.append(f"{i + 1}a")
                        corelist.append(f"{i + 1}b")
                    table = pd.DataFrame(
                        index=range(terminals),
                        data={
                            "ROW": "D",
                            "POS": range(1, terminals + 1),
                            "FUNCTION": "SPARE",
                            "TYPE": "TERMINAL",
                            "CABLE NAME": cablename,
                            "CABLE PAIR": row["CableBoxQ"],
                            "CABLE DEST": f"DB {row['SignalName']}",
                            "CORE": corelist,
                            "SHEET": "-",
                        },
                    )
                    dir = str(row["Dir"].lower() if pd.notna(row["Dir"]) else "")
                    characters = row["Aspect"] + dir
                    function = []
                    for character in characters:
                        function.extend(
                            [
                                f"{row['SignalName'][:-1]}{functiondict[character][0]}",
                                f"{row['SignalName'][:-1]}{functiondict[character][1]}",
                            ]
                        )
                    # CORE list
                    row_count = len(function)
                    indexes = range(last_row, last_row + row_count)
                    table.loc[indexes, "FUNCTION"] = function
                    table.loc[indexes, "TYPE"] = "TERMINAL"
                    table.loc[indexes, "SHEET"] = row["Sheet"]
                    last_row += row_count
                    tables.append(table)
        df = pd.concat(tables, ignore_index=True)
        df["POS"] = range(1, len(df) + 1)
        return df

    def split_df(self):
        dfs: list[pd.DataFrame] = [
            group
            for _, group in self.df.groupby(["CABLE NAME"], sort=False, dropna=False)
        ]
        split_dfs: list[pd.DataFrame] = []
        for df in dfs:
            split_dfs.extend(
                group for _, group in df.groupby(np.arange(len(df)) // self.MAX_ROWS)
            )
        index = 0
        while index + 1 < len(split_dfs):
            df_current = split_dfs[index]
            df_next = split_dfs[index + 1]
            if len(df_current) + len(df_next) <= self.MAX_ROWS:
                split_dfs[index] = pd.concat([df_current, df_next])
                split_dfs.pop(index + 1)
            else:
                index += 1
        return split_dfs

    def build_blocks(self):
        # Iterate through list to isolate dataframe to a sheet
        blocks = []

        for sheetindex, dataframe in enumerate(self.df_split, start=1):
            # Seperate it per line of dataframe
            rows = dataframe.to_dict("records")
            blockdatalist = []
            # Borderblock values
            self.bordervalues["BORDER_SHEET"] = f"R{self.sheet:03d}"
            blockdatalist.append(["PSP_BORDER_BLOCK", (0, 0), self.bordervalues.copy()])
            self.sheet += 1
            blockdatalist.append(
                [
                    "OP_BASE",
                    (0, 0),
                    {
                        "TABLE_HEAD": f"OP 11 - {dataframe['ROW'].iloc[0]}",
                    },
                ]
            )
            blockdatalist.append(
                [
                    "BORDER_INDEX_NAME",
                    (0, 0),
                    {
                        "BORDER_INDEX_NAME": f"OP 11 - D STRIP ANALYSIS ({sheetindex} OF {len(self.df_split)})",
                    },
                ]
            )
            cablestart_index = 0
            for i, row in enumerate(rows):
                block = []
                row2 = rows[i + 1] if i + 1 < len(rows) else {"CABLE NAME": ""}
                blockdict = {
                    "A1": row["ROW"],
                    "A2": row["POS"],
                    "A3": row["FUNCTION"],
                    "A4": row["TYPE"],
                    "A5": row["CORE"],
                    "A6": row["SHEET"],
                    "CABLENAME_L1": row["CABLE NAME"],
                    "CABLENAME_L2": row["CABLE PAIR"],
                    "CABLENAME_L3": row["CABLE DEST"],
                }

                if row["CABLE NAME"] == row2["CABLE NAME"]:
                    block.append(
                        ["OPSIG_TABLE_6_1_START", (96, 236 - 5 * i), blockdict]
                    )
                else:
                    block.append(["OPSIG_TABLE_6_1_END", (96, 236 - 5 * i), blockdict])
                    block.append(
                        [
                            "OPSIG_CABLENAME",
                            (228, 236 - 5 * (cablestart_index + i + 2) / 2),
                            blockdict,
                        ]
                    )
                    cablestart_index = i
                blockdatalist.extend(block)
            blocks.append(blockdatalist)
        return blocks


#########################
# Points OP sheets
# Max 40 terminals per sheet
########################
class OPPointsSheet:
    def __init__(self, dataframe, bordervalues, sheet):
        self.MAX = 14
        self.MAX_PER_SHEET = 10
        self.dataframe = dataframe
        self.bordervalues = bordervalues
        self.sheet = sheet
        self.op_numbers = {}
        self.df_split = self.split_df()
        self.blocks = self.build_blocks()
        self.next_sheet = self.sheet

    def split_df(self):
        df_split = [
            group.sort_values("CableBox", key=lambda x: x.str.split(".").str[-1])
            for _, group in self.dataframe.groupby(
                self.dataframe.index // self.MAX_PER_SHEET
            )
        ]
        return df_split

    def build_blocks(self):
        # Iterate through list to isolate dataframe to a sheet
        blocks = []
        prevpos = 0
        for sheetindex, dataframe in enumerate(self.df_split, start=1):
            blockdatalist = []
            self.bordervalues["BORDER_SHEET"] = f"R{self.sheet:03d}"
            blockdatalist.append(["PSP_BORDER_BLOCK", (0, 0), self.bordervalues.copy()])
            self.sheet += 1
            blockdatalist.append(
                [
                    "OP_BASE",
                    (0, 0),
                    {
                        "TABLE_HEAD": f"OP 11 - {dataframe['OPRow'].iloc[0][0]}",
                    },
                ]
            )
            blockdatalist.append(
                [
                    "BORDER_INDEX_NAME",
                    (0, 0),
                    {
                        "BORDER_INDEX_NAME": f"OP 11 - {dataframe['OPRow'].iloc[0][0]} STRIP ANALYSIS ({sheetindex} OF {len(self.df_split)})"
                    },
                ]
            )
            for i, (_, row) in enumerate(dataframe.iterrows()):
                self.op_numbers[row["Sheet"]] = prevpos + 1
                blockdatalist.append(
                    [
                        "OPPOINT_TABLE",
                        (0, 0 - 20 * i),
                        {
                            **{f"A1_{e}": row["OPRow"][0] for e in range(1, 5)},
                            **{f"A2_{i}": f"{prevpos + i}" for i in range(1, 5)},
                            **{
                                f"A3_{e}": f"{row['PointName']} - W{e}"
                                for e in range(1, 5)
                            },
                            **{f"A6_{e}": row["Sheet"] for e in range(1, 5)},
                            "CABLENAME_L1": row["CableBox"],
                            "CABLENAME_L2": "4c",
                            "CABLENAME_L3": row["PointName"],
                        },
                    ]
                )
                prevpos += 4
            blocks.append(blockdatalist)
        return blocks


#########################
# Counters OP sheets
# Max 40 terminals per sheet
########################
class OPCountersSheet:
    def __init__(self, dataframe, bordervalues, sheet):
        self.MAX = 14
        self.MAX_PER_SHEET = 10
        self.dataframe = dataframe
        self.bordervalues = bordervalues
        self.sheet = sheet
        self.op_numbers = {}
        self.df = self.build_df()
        self.df_split = self.split_df()
        self.blocks = self.build_blocks()
        self.next_sheet = self.sheet

    def build_df(self):
        dfs = [
            group.sort_values("Qn")
            if not pd.isna(group["CableAppCase"].iloc[0])
            else group.sort_values(
                "CableBox", key=lambda x: x.str.split(".").str[-1].astype(int)
            )
            for _, group in self.dataframe.groupby("CableAppCase", dropna=False)
        ]
        df = pd.concat(dfs, ignore_index=True)
        return df

    def split_df(self):
        dfs = [
            group
            for _, group in self.df.groupby(["CableAppCase"], sort=False, dropna=False)
        ]
        # Add the spare rows for appcases
        for df in dfs:
            if pd.notna(df["CableAppCase"].iloc[0]):  # is Appcase
                q = df["Q"].iloc[0]
                qn = df["Qn"].iloc[-1]
                for i in range(int(q - qn)):
                    df.loc[df.index.max() + 1] = {
                        "OP": df["OP"].iloc[0],
                        "CableAppCase": df["CableAppCase"].iloc[0],
                        "Sheet": "-",
                        "Q": q,
                        "Qn": qn + i + 1,
                    }
        split_df = []
        for df in dfs:
            split_df.extend(
                group
                for _, group in df.groupby(np.arange(len(df)) // self.MAX_PER_SHEET)
            )
        index = 0
        while index + 1 < len(split_df):
            df_current = split_df[index]
            df_next = split_df[index + 1]
            if len(df_current) + len(df_next) <= self.MAX_PER_SHEET:
                split_df[index] = pd.concat([df_current, df_next])
                split_df.pop(index + 1)
            else:
                index += 1
        return split_df

    def build_blocks(self):
        # Iterate through list to isolate dataframe to a sheet
        blocks = []
        prevpos = 0
        for sheetindex, dataframe in enumerate(self.df_split, start=1):
            blockdatalist = []
            self.bordervalues["BORDER_SHEET"] = f"R{self.sheet:03d}"
            blockdatalist.append(["PSP_BORDER_BLOCK", (0, 0), self.bordervalues.copy()])
            self.sheet += 1
            blockdatalist.append(
                [
                    "OP_BASE",
                    (0, 0),
                    {
                        "TABLE_HEAD": f"OP 11 - {str(dataframe['OP'].iloc[0])[-1]}",
                    },
                ]
            )
            blockdatalist.append(
                [
                    "BORDER_INDEX_NAME",
                    (0, 0),
                    {
                        "BORDER_INDEX_NAME": f"OP 11 - {str(dataframe['OP'].iloc[0])[-1]} STRIP ANALYSIS ({sheetindex} OF {len(self.df_split)})",
                    },
                ]
            )
            cablestart_index = 0
            for i, (_, row) in enumerate(dataframe.iterrows()):
                # If appcase and not last in df or last in appcase
                # Return False if end of Cable or end of df
                isend = (
                    pd.notna(dataframe["Qn"].iloc[i + 1])
                    if i + 1 < len(dataframe)
                    else False
                )
                if not isend:
                    if pd.isna(row["CableAppCase"]):
                        cable_l1 = row["CableBox"]
                        cable_l2 = "1Q"
                    else:
                        cable_l1 = row["CableAppCase"]
                        cable_l2 = f"{row['Q']:.0f}Q"
                    blockdatalist.append(
                        [
                            "OPSIG_CABLENAME",
                            (228, 224.5 - 10 * (i + cablestart_index)),
                            {
                                "CABLENAME_L1": cable_l1,
                                "CABLENAME_L2": cable_l2,
                                "CABLENAME_L3": "",
                            },
                        ]
                    )
                    cablestart_index = i + 1
                self.op_numbers[row["Sheet"]] = prevpos + 1
                blockdatalist.append(
                    [
                        "OPAXLE_TABLE_START"
                        if pd.notna(row["Qn"]) and isend
                        else "OPAXLE_TABLE_END",
                        (96, 236 - 20 * i),
                        {
                            **{f"A1_{i}": str(row["OP"])[-1] for i in range(1, 5)},
                            **{f"A2_{i}": f"{prevpos + i}" for i in range(1, 5)},
                            "A3_1": f"{row['AZgr']:.0f}/{row['AZnr']:.0f}AZ SYS 1"
                            if pd.notna(row["AZgr"])
                            else "SPARE",
                            "A3_2": f"{row['AZgr']:.0f}/{row['AZnr']:.0f}AZ SYS 2"
                            if pd.notna(row["AZgr"])
                            else "SPARE",
                            "A3_3": f"{row['AZgr']:.0f}/{row['AZnr']:.0f}AZ Vcc"
                            if pd.notna(row["AZgr"])
                            else "SPARE",
                            "A3_4": f"{row['AZgr']:.0f}/{row['AZnr']:.0f}AZ GND"
                            if pd.notna(row["AZgr"])
                            else "SPARE",
                            "A5": f"Q{row['Qn']:.0f}" if pd.notna(row["Qn"]) else "Q1",
                            **{f"A6_{i}": f"{row['Sheet']}" for i in range(1, 5)},
                        },
                    ]
                )
                prevpos += 4

            blocks.append(blockdatalist)
        return blocks


###############################################################################
# Cabinet Layout
###############################################################################
class CabinetSheet:
    pass


###############################################################################
# A - Power Rack layout
###############################################################################
class PowerRackSheet:
    def __init__(self, dataframe, bordervalues, sheet):
        self.dataframe = dataframe
        self.bordervalues = bordervalues
        self.sheet = sheet + 1
        self.blocks = self.build_blocks()
        self.next_sheet = self.sheet

    def build_blocks(self):
        blocks = []
        loc = self.dataframe["LOC"].iloc[0]
        blockdatalist = []
        self.bordervalues["BORDER_SHEET"] = f"R{self.sheet:03d}"
        blockdatalist.append(["PSP_BORDER_BLOCK", (0, 0), self.bordervalues.copy()])
        self.sheet += 1
        blockdatalist.append(
            ["POWER_RACK_SHEET_BASE", (0, 0), {"LOC": f"RSS LOC-{loc}"}]
        )
        blockdatalist.append(
            [
                "BORDER_INDEX_NAME",
                (0, 0),
                {
                    "BORDER_INDEX_NAME": "A - POWER RACK LAYOUT",
                },
            ]
        )
        blocks.append(blockdatalist)
        return blocks


###############################################################################
# C - IO Rack layout
###############################################################################
class IORackSheet:
    def __init__(self, dataframe, bordervalues, sheet):
        self.dataframe = dataframe
        self.bordervalues = bordervalues
        self.sheet = sheet
        self.blocks = self.build_blocks()
        self.next_sheet = self.sheet

    def build_blocks(self):
        blocks = []
        loc = self.dataframe["LOC"].iloc[0]
        blockdatalist = []
        self.bordervalues["BORDER_SHEET"] = f"R{self.sheet:03d}"
        blockdatalist.append(["PSP_BORDER_BLOCK", (0, 0), self.bordervalues.copy()])
        self.sheet += 1
        blockdatalist.append(["IO_RACK_SHEET_BASE", (0, 0), {"LOC": f"RSS LOC-{loc}"}])
        blockdatalist.append(
            [
                "BORDER_INDEX_NAME",
                (0, 0),
                {
                    "BORDER_INDEX_NAME": "C - IO RACK LAYOUT",
                },
            ]
        )
        blocks.append(blockdatalist)
        return blocks


###############################################################################
# D - Points Rack Layout
###############################################################################
class PointsRackSheet:
    def __init__(self, dataframe, bordervalues, sheet):
        self.dataframe = dataframe
        self.bordervalues = bordervalues
        self.sheet = sheet
        self.blocks = self.build_blocks()
        self.next_sheet = self.sheet

    def build_blocks(self):
        blocks = []
        loc = self.dataframe["LOC"].iloc[0]
        blockdatalist = []
        self.bordervalues["BORDER_SHEET"] = f"R{self.sheet:03d}"
        blockdatalist.append(["PSP_BORDER_BLOCK", (0, 0), self.bordervalues.copy()])
        self.sheet += 1
        blockdatalist.append(
            [
                "POINTS_RACK_SHEET_BASE",
                (0, 0),
                {
                    "LOC": f"RSS LOC-{loc}",
                    **{f"IO_RACK_SHEET_PCM0{i + 1}": "SPARE" for i in range(9)},
                    **{
                        f"IO_RACK_SHEET_PCM0{i + 1}": f"PCM 0{i + 1}"
                        for i in range(len(self.dataframe))
                    },
                    **{
                        f"IO_RACK_SHEET_PCM0{i + 1}_POINT": f"{self.dataframe['PointName'].iloc[i]}"
                        for i in range(len(self.dataframe))
                    },
                },
            ]
        )
        blockdatalist.append(
            [
                "BORDER_INDEX_NAME",
                (0, 0),
                {
                    "BORDER_INDEX_NAME": "D - POINTS RACK LAYOUT",
                },
            ]
        )
        blocks.append(blockdatalist)
        return blocks


###############################################################################
# E - Signals Rack Layout
###############################################################################
class SignalsRackSheet:
    def __init__(self, dataframe, bordervalues, sheet):
        self.dataframe = dataframe
        self.bordervalues = bordervalues
        self.sheet = sheet
        self.df_split = self.split_df()
        self.blocks = self.build_blocks()
        self.next_sheet = self.sheet

    def split_df(self):
        dfs = [
            group
            for _, group in self.dataframe.groupby(["SCM"], sort=False, dropna=False)
        ]
        return dfs

    def build_blocks(self):
        # Iterate through list to isolate dataframe to a sheet
        blocks = []
        loc = self.dataframe["LOC"].iloc[0]
        blockdatalist = []
        self.bordervalues["BORDER_SHEET"] = f"R{self.sheet:03d}"
        blockdatalist.append(["PSP_BORDER_BLOCK", (0, 0), self.bordervalues.copy()])
        self.sheet += 1
        blockdatalist.append(
            [
                "SIGNALS_RACK_SHEET_BASE",
                (0, 0),
                {
                    "LOC": f"RSS LOC-{loc}",
                },
            ]
        )
        blockdatalist.append(
            [
                "BORDER_INDEX_NAME",
                (0, 0),
                {
                    "BORDER_INDEX_NAME": "E - SIGNSLS RACK LAYOUT",
                },
            ]
        )

        scm_count = 1
        for scm_columndf in self.df_split:
            scm_columndf = scm_columndf.fillna("")
            if len(scm_columndf) < 2:
                signal1 = scm_columndf["SignalName"].iloc[0][:-1]
                signal2 = scm_columndf["SignalName"].iloc[0][:-1]
                aspect1 = scm_columndf["Aspect"].iloc[0]
                aspect2 = str(scm_columndf["Dir"].iloc[0]).lower()
            else:
                signal1 = scm_columndf["SignalName"].iloc[0][:-1]
                signal2 = scm_columndf["SignalName"].iloc[1][:-1]
                aspect1 = scm_columndf["Aspect"].iloc[0]
                aspect2 = scm_columndf["Aspect"].iloc[1]

            def get_scm_list(signal, aspect):
                scmdict = {
                    "GHR": [
                        f"{signal} RG",
                        f"{signal} HG",
                        f"{signal} DG",
                        "-",
                        "-",
                    ],
                    "HR": [
                        f"{signal} RG",
                        f"{signal} HG",
                        "-",
                        "-",
                        "-",
                    ],
                    "R": [
                        f"{signal} RG",
                        "-",
                        "-",
                        "-",
                        "-",
                    ],
                    "lsr": [
                        "-",
                        f"{signal} (L)UG",
                        f"{signal} (↑)UG",
                        "-",
                        f"{signal} (R)UG",
                    ],
                    "ls": [
                        "-",
                        f"{signal} (L)UG",
                        f"{signal} (↑)UG",
                        "-",
                        "-",
                    ],
                    "sr": [
                        "-",
                        f"{signal} (↑)UG",
                        f"{signal} (R)UG",
                        "-",
                        "-",
                    ],
                    "lr": [
                        "-",
                        f"{signal} (L)UG",
                        f"{signal} (R)UG",
                        "-",
                        "-",
                    ],
                    "": [
                        "-",
                        "-",
                        "-",
                        "-",
                        "-",
                    ],
                }
                return scmdict[aspect]

            scmlist = get_scm_list(signal1, aspect1) + get_scm_list(signal2, aspect2)

            blockdatalist.append(
                [
                    "SIGNALS_RACK_SHEET_TABLE",
                    (0 + 28 * (scm_count - 1), 0),
                    {
                        "SIGNALS_RACK_SHEET_SCM01_0": f"SCM {scm_count:02d}",
                        **{
                            f"SIGNALS_RACK_SHEET_SCM01_{i}": e
                            for i, e in enumerate(scmlist, start=1)
                        },
                    },
                ]
            )
            scm_count += 1
        while scm_count <= 12:
            blockdatalist.append(
                [
                    "SIGNALS_RACK_SHEET_TABLE_SPARE",
                    (0 + 28 * (scm_count - 1), 0),
                    {"SIGNALS_RACK_SHEET_SCM01_0": f"SCM {scm_count:02d}"},
                ]
            )
            scm_count += 1
        blocks.append(blockdatalist)
        return blocks


###############################################################################
# ROW A, B, C, D, E, F, G, H, J, K, L, M, N & P Strip Analysis
###############################################################################
class StripRackSheet:
    def __init__(self, dataframe, bordervalues, sheet):
        self.MAX_ROWS = 47
        self.dataframe = dataframe
        self.bordervalues = bordervalues
        self.sheet = sheet
        self.blank_dfs = self._blank_dfs()
        self.dfs = self.build_dfs()
        self.df_split = self.split_df()
        self.blocks = self.build_blocks()
        self.next_sheet = self.sheet

    # Use the build_df function to build the base dataframes for each row, for the entire A-P Rows of the table
    # This dataframe is the minimal possible, don't consider the signals/points
    # Rows with varying sizes:
    #   - K/L (Points circuit breakers)
    #   - M/N (Signals circuit breakers)
    def _blank_dfs(self):
        loc = self.dataframe["D"]["LOC"].iloc[0]
        df_A = pd.DataFrame(
            {
                "ROW": ["A"] * 7,
                "POS": ["-", *range(1, 7)],
                "FUNCTION": ["POWER RACK"] + ["LPSM"] * 4 + ["FPSM"] * 2,
                "TYPE": ["VM1000"] + ["VM1102"] * 4 + ["VM1112"] * 2,
                "SHEET": ["-"] * 7,
            }
        )
        df_B = pd.DataFrame(
            {
                "ROW": ["B"],
                "POS": ["-"],
                "FUNCTION": ["BLANK PANEL"],
                "TYPE": ["-"],
                "SHEET": ["-"],
            }
        )
        df_C = pd.DataFrame(
            {
                "ROW": ["C"] * 16,
                "POS": ["-", *range(1, 16)],
                "FUNCTION": [
                    "IO RACK",
                    "PSM",
                    "A-QEXM",
                    "A-SPM",
                    "B-SPM",
                    "B-QEXM",
                    *["BLANK PANEL"] * 8,
                    "BLANK PANEL",
                    "BLANK PANEL",
                ],
                "TYPE": [
                    "VM1068",
                    "VM1905",
                    "VM1322",
                    "VM1902",
                    "VM1902",
                    "VM1322",
                    *["TC2801"] * 8,
                    "TMC-001",
                    "TMC-001",
                ],
                "SHEET": ["-"] * 16,
            }
        )
        df_D = pd.DataFrame(
            {
                "ROW": ["D"] * 10,
                "POS": ["-", *range(1, 10)],
                "FUNCTION": ["POINTS RACK"] + ["BLANK PANEL"] * 9,
                "TYPE": ["VM1056"] + ["VC201"] * 9,
                "SHEET": ["-"] * 10,
            }
        )
        df_E = pd.DataFrame(
            {
                "ROW": ["E"] * 13,
                "POS": ["-", *range(1, 13)],
                "FUNCTION": ["SIGNALS RACK"] + ["BLANK PANEL"] * 12,
                "TYPE": [
                    "VM1057",
                    *["VM1501"] * 8,
                    *["VC200"] * 4,
                ],
                "SHEET": ["-"] * 13,
            }
        )
        df_F = pd.DataFrame(
            {
                "ROW": ["F"] * 9,
                "POS": ["-", *range(1, 9)],
                "FUNCTION": [
                    "220VAC POWER DISTRIBUTION",
                    "LIGHTING PROTECTION MODULE",
                    "MAIN POWER-I",
                    "POWER RACK-I",
                    "VDN SWITCH-I",
                    "MAIN POWER-II",
                    "POWER RACK-II",
                    "VDN SWITCH-II",
                    "FAN",
                ],
                "TYPE": [
                    "-",
                    "LIGHTING PROTECTION MODULE",
                    *["CIRCUIT BREAKER"] * 7,
                ],
                "SHEET": ["-"] * 9,
            }
        )
        df_G = pd.DataFrame(
            {
                "ROW": ["G"],
                "POS": ["U60 - U83"],
                "FUNCTION": ["INTERNAL WIRING"],
                "TYPE": ["TERMINALS"],
                "SHEET": ["-"],
            }
        )
        df_H = pd.DataFrame(
            {
                "ROW": ["H"] * 8,
                "POS": list(range(1, 9)),
                "FUNCTION": [
                    "VOLTAGE MONITOR",
                    "VOLTAGE MONITOR",
                    "24V POWER SUPPLY",
                    "24V POWER SUPPLY",
                    "24V POWER SUPPLY",
                    f"LOC-{loc} VDN SWITCH A",
                    f"LOC-{loc} VDN SWITCH B",
                    f"LOC-{loc} S&D SWITCH",
                ],
                "TYPE": [
                    "VM-1923-1",
                    "VM-1923-2",
                    *["QS10.241"] * 3,
                    "-",
                    "-",
                    "-",
                ],
                "SHEET": [
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "T002",
                    "T002",
                    "T002",
                ],
            }
        )
        df_J = pd.DataFrame(
            {
                "ROW": ["J"],
                "POS": ["-"],
                "FUNCTION": ["BLANK"],
                "TYPE": ["-"],
                "SHEET": ["-"],
            }
        )
        df_K = pd.DataFrame(
            {
                "ROW": ["K"],
                "POS": ["-"],
                "FUNCTION": ["BLANK"],
                "TYPE": ["-"],
                "SHEET": ["-"],
            }
        )
        df_L = pd.DataFrame(
            {
                "ROW": ["L"],
                "POS": ["-"],
                "FUNCTION": ["BLANK"],
                "TYPE": ["-"],
                "SHEET": ["-"],
            }
        )
        df_M = pd.DataFrame(
            {
                "ROW": ["M"],
                "POS": ["-"],
                "FUNCTION": ["BLANK"],
                "TYPE": ["-"],
                "SHEET": ["-"],
            }
        )
        df_N = pd.DataFrame(
            {
                "ROW": ["N"],
                "POS": ["-"],
                "FUNCTION": ["BLANK"],
                "TYPE": ["-"],
                "SHEET": ["-"],
            }
        )

        df_P = pd.DataFrame(
            {
                "ROW": ["P"] * 14,
                "POS": [
                    "U97",
                    "U96",
                    "U95",
                    "U94",
                    "U93",
                    "U92",
                    "U91",
                    "U90",
                    "U44 - U33",
                    "U4",
                    "U3",
                    "U2",
                    "U1",
                    "1 - 3",
                ],
                "FUNCTION": [
                    "CX230V - POINTS POWER SUPPLY",
                    "BX230V - POINTS POWER SUPPLY",
                    "400VAC_N - POINTS POWER SUPPLY",
                    "400VAC_L3 - POINTS POWER SUPPLY",
                    "400VAC_L2 - POINTS POWER SUPPLY",
                    "400VAC_L1 - POINTS POWER SUPPLY",
                    "CX110V - SIGNALS POWER SUPPLY",
                    "BX110V - SIGNALS POWER SUPPLY",
                    "INTERNAL WIRING",
                    "CX230V INPUT POWER 2",
                    "BX230V INPUT POWER 2",
                    "CX230V INPUT POWER 1",
                    "BX230V INPUT POWER 1",
                    "LIGHTNING PROTECTION MODULE",
                ],
                "TYPE": ["TERMINALS"] * 14,
                "SHEET": [
                    *["N00X"] * 8,
                    "-",
                    *["N00X"] * 4,
                    "-",
                ],
            }
        )
        dfs = {
            "A": df_A,
            "B": df_B,
            "C": df_C,
            "D": df_D,
            "E": df_E,
            "F": df_F,
            "G": df_G,
            "H": df_H,
            "J": df_J,
            "K": df_K,
            "L": df_L,
            "M": df_M,
            "N": df_N,
            "P": df_P,
        }
        return dfs

    # using the self.blank_dfs["A","B", ...] maninpulate the dataframes
    # Most dfs stay the same, except for ("D", "E", "K", "L", "M", "N")
    def build_dfs(self):
        ####################### D #######################
        for i, e in self.dataframe["E"].iterrows():
            update = {
                "FUNCTION": f"PCM {i + 1} ({e['PointName']})",
                "TYPE": "VM1514",
                "SHEET": e["Sheet"],
            }
            self.blank_dfs["D"].loc[i + 1, update.keys()] = update.values()

        ####################### E #######################
        for i, (_, e) in enumerate(
            [group for group in self.dataframe["D"].groupby("SCM")]
        ):
            update = {
                "FUNCTION": f"SCM {i + 1} ({e['SignalName'].iloc[0]})"
                if len(e) < 2
                else f"SCM {i + 1} ({e['SignalName'].iloc[0]} / {e['SignalName'].iloc[1]})",
                "TYPE": "VM1501",
                "SHEET": e["Sheet"].iloc[0]
                if len(e) < 2
                else f"{e['Sheet'].iloc[0]} / {e['Sheet'].iloc[1]}",
            }
            self.blank_dfs["E"].loc[i + 1, update.keys()] = update.values()

            ####################### K #######################
        update = {
            "ROW": "K",
            "POS": "U120-U127",
            "FUNCTION": "INTERNAL WIRING",
            "TYPE": "-",
            "SHEET": "N00X",
        }
        self.blank_dfs["K"] = pd.DataFrame([update])
        for i, e in self.dataframe["E"].iloc[:4].iterrows():
            update = {
                "ROW": "K",
                "POS": f"K{2 * i + 1}",
                "FUNCTION": f"230VAC - {e['PointName']}",
                "TYPE": "CIRCUIT BREAKER 0.5A - 1 POLE",
                "SHEET": "N00X",
            }
            self.blank_dfs["K"].loc[len(self.blank_dfs["K"]), update.keys()] = (
                update.values()
            )
            update = {
                "ROW": "K",
                "POS": f"K{2 * i + 2}",
                "FUNCTION": f"400VAC - {e['PointName']}",
                "TYPE": "CIRCUIT BREAKER 5A - 3 POLE",
                "SHEET": "N00X",
            }
            self.blank_dfs["K"].loc[len(self.blank_dfs["K"]), update.keys()] = (
                update.values()
            )
        self.blank_dfs["K"] = self.blank_dfs["K"][::-1]
        ####################### L #######################
        if len(self.dataframe["E"].iloc[4:]) > 0:
            self.blank_dfs["L"] = pd.DataFrame()
        for i, e in self.dataframe["E"].iloc[4:].iterrows():
            update = {
                "ROW": "L",
                "POS": f"K{2 * i + 1}",
                "FUNCTION": f"230VAC - {e['PointName']}",
                "TYPE": "CIRCUIT BREAKER 0.5A - 1 POLE",
                "SHEET": "N00X",
            }
            self.blank_dfs["L"].loc[len(self.blank_dfs["L"]), update.keys()] = (
                update.values()
            )
            update = {
                "ROW": "L",
                "POS": f"K{2 * i + 2}",
                "FUNCTION": f"400VAC - {e['PointName']}",
                "TYPE": "CIRCUIT BREAKER 5A - 3 POLE",
                "SHEET": "N00X",
            }
            self.blank_dfs["L"].loc[len(self.blank_dfs["L"]), update.keys()] = (
                update.values()
            )
        self.blank_dfs["L"] = self.blank_dfs["L"][::-1]
        ####################### M #######################
        update = {
            "ROW": "M",
            "POS": "U110-U113",
            "FUNCTION": "INTERNAL WIRING",
            "TYPE": "TERMINALS",
            "SHEET": "-",
        }
        self.blank_dfs["M"] = pd.DataFrame([update])
        for i, e in self.dataframe["D"].iloc[:10].iterrows():
            update = {
                "ROW": "M",
                "POS": f"K{i + 1}",
                "FUNCTION": e["SignalName"],
                "TYPE": "CIRCUIT BREAKER 1A - 2 POLE"
                if pd.isna(e["Dir"])
                else "CIRCUIT BREAKER 2A - 2 POLE",
                "SHEET": "N00X",
            }
            self.blank_dfs["M"].loc[len(self.blank_dfs["M"]), update.keys()] = (
                update.values()
            )
        self.blank_dfs["M"] = self.blank_dfs["M"][::-1]
        ####################### N #######################
        if len(self.dataframe["D"].iloc[4:]) > 0:
            self.blank_dfs["N"] = pd.DataFrame()
        for i, e in self.dataframe["D"].iloc[10:].iterrows():
            update = {
                "ROW": "N",
                "POS": f"K{i + 1}",
                "FUNCTION": e["SignalName"],
                "TYPE": "CIRCUIT BREAKER 1A - 2 POLE"
                if pd.isna(e["Dir"])
                else "CIRCUIT BREAKER 2A - 2 POLE",
                "SHEET": "N00X",
            }
            self.blank_dfs["N"].loc[len(self.blank_dfs["N"]), update.keys()] = (
                update.values()
            )
        self.blank_dfs["N"] = self.blank_dfs["N"][::-1]

    # From self.blank_dfs use the combine code from OPSignalsSheet
    # create dataframe for every sheet tables
    def split_df(self):
        split_dfs = list(self.blank_dfs.values())
        index = 0
        while index + 1 < len(split_dfs):
            df_current = split_dfs[index]
            df_next = split_dfs[index + 1]
            if len(df_current) + len(df_next) <= self.MAX_ROWS:
                split_dfs[index] = pd.concat([df_current, df_next], ignore_index=True)
                split_dfs.pop(index + 1)
            else:
                index += 1
        return split_dfs

    def build_blocks(self):
        blocks = []
        for sheetindex, dataframe in enumerate(self.df_split, start=1):
            blockdatalist = []
            # Borderblock values
            self.bordervalues["BORDER_SHEET"] = f"R{self.sheet:03d}"
            blockdatalist.append(["PSP_BORDER_BLOCK", (0, 0), self.bordervalues.copy()])
            self.sheet += 1
            loc = self.dataframe["D"]["LOC"].iloc[0]
            blockdatalist.append(
                [
                    "STRIP_ANALYSIS_TABLE_HEAD",
                    (0, 0),
                    {"TABLE_HEADING": f"RSS LOC-{loc} CABINET"},
                ]
            )
            # INDEX NAME

            rows: list[str] = [row for row, _ in dataframe.groupby("ROW")]
            formated_rows: str = ", ".join(rows[:-1])
            if len(rows) > 1:
                formated_rows: str = f"{formated_rows} & {rows[-1]}"
            else:
                formated_rows = rows[0]
            blockdatalist.append(
                [
                    "BORDER_INDEX_NAME",
                    (0, 0),
                    {
                        "BORDER_INDEX_NAME": f"RSS LOC-{loc} CABINET - ROW {formated_rows} STRIP ANALYSIS"
                    },
                ]
            )
            for i, df_row in dataframe.iterrows():
                blockdatalist.append(
                    [
                        "STRIP_ANALYSIS_TABLE_ROW",
                        (0, -5 * i),
                        {
                            "A1": df_row["ROW"],
                            "A2": df_row["POS"],
                            "A3": df_row["FUNCTION"],
                            "A4": df_row["TYPE"],
                            "A5": df_row["SHEET"],
                        },
                    ]
                )
            blocks.append(blockdatalist)
        return blocks


###############################################################################
# Axle Counter Cabinet Layout
###############################################################################
class AxleCabinetSheet:
    def __init__(self, dataframe, bordervalues, sheet):
        self.dataframe = dataframe
        self.bordervalues = bordervalues
        self.sheet = sheet
        # self.dfs = self.build_dfs()
        # self.df_split = self.split_df()
        # self.blocks = self.build_blocks()
        self.next_sheet = self.sheet + 1


###############################################################################
# FADC COUNTER RACK
###############################################################################
class AxleFADCSheet:
    def __init__(self, dataframe, bordervalues, sheet):
        self.dataframe = dataframe
        self.bordervalues = bordervalues
        self.sheet = sheet
        self.dfs = self.build_dfs()
        self.blocks = self.build_blocks()
        self.next_sheet = self.sheet

    # Create list of dataframes, grouped by the ["AZgr"] and ["FADC"] sorted by ["AEB"]
    def build_dfs(self):
        _i = [group for _, group in self.dataframe.groupby("AZgr", sort=False)]
        dfs = []
        for df in _i:
            dfs.append(
                [
                    group.sort_values("AEB")
                    for _, group in df.groupby("FADC", sort=False)
                ]
            )
        return dfs

    def build_blocks(self):
        blocks = []
        for sheetindex, dataframe in enumerate(self.dfs):
            blockdatalist = []
            self.bordervalues["BORDER_SHEET"] = f"R{self.sheet:03d}"
            blockdatalist.append(["PSP_BORDER_BLOCK", (0, 0), self.bordervalues.copy()])
            self.sheet += 1
            side1 = dataframe[0]
            side1[["FM1", "FM2"]] = (
                side1[["FM1", "FM2"]].fillna("").map(lambda x: f" ({x})" if x else "")
            )
            side2 = dataframe[1]
            side2[["FM1", "FM2"]] = (
                side2[["FM1", "FM2"]].fillna("").map(lambda x: f" ({x})" if x else "")
            )
            blockdatalist.append(
                [
                    "BORDER_INDEX_NAME",
                    (0, 0),
                    {
                        "BORDER_INDEX_NAME": f"{side1['FADC'].iloc[0][0]} - FADC AXLE COUNTER {side1['AZgr'].iloc[0]} RACK LAYOUT",
                    },
                ]
            )
            blockdatalist.append(
                [
                    "AXLE_FADC_SHEET_BASE",
                    (0, 0),
                    {
                        "AXLE_FADC_SHEET_HEADING": f"{side1['FADC'].iloc[0][0]} - FADC AXLE COUNTER {side1['AZgr'].iloc[0]} RACK (FRONT VIEW)",
                        "AXLE_FADC_SHEET_SIDE1": f"{side1['FADC'].iloc[0]}",
                        "AXLE_FADC_SHEET_SIDE1_1": f"{side1['FADC'].iloc[0]}",
                        "AXLE_FADC_SHEET_SIDE2": f"{side2['FADC'].iloc[0]}",
                        "AXLE_FADC_SHEET_SIDE2_1": f"{side2['FADC'].iloc[0]}",
                        **{
                            f"AXLE_FADC_SHEET_DIP_A1_{i + 3}": f"AEB{side1['AEB'].iloc[i]}-{side1['AZgr'].iloc[i]}/{side1['AZnr'].iloc[i]}"
                            if i < len(side1)
                            else f"AEB{i + 3}-"
                            for i in range(7)
                        },
                        **{
                            f"AXLE_FADC_SHEET_DIP_A2_{i + 2}": f"AEB{side2['AEB'].iloc[i]}-{side2['AZgr'].iloc[i]}/{side2['AZnr'].iloc[i]}"
                            if i < len(side2)
                            else f"AEB{i + 2}-"
                            for i in range(7)
                        },
                    },
                ]
            )
            for i in range(6):
                blockdatalist.append(
                    [
                        "AXLE_FADC_SHEET_AEB"
                        if i < len(side1)
                        else "AXLE_FADC_SHEET_AEB_SPARE",
                        (13.25 * i, 0),
                        {
                            "AXLE_FADC_SHEET_ID": f"{side1['AZgr'].iloc[i]}/{side1['AZnr'].iloc[i]}"
                            if i < len(side1)
                            else "",
                            "AXLE_FADC_SHEET_TRACK": f"{side1['Track1'].iloc[i]}{side1['FM1'].iloc[i]} / {side1['Track2'].iloc[i]}{side1['FM2'].iloc[i]}"
                            if i < len(side1)
                            else "",
                        },
                    ]
                )
            for i in range(7):
                blockdatalist.append(
                    [
                        "AXLE_FADC_SHEET_AEB"
                        if i < len(side2)
                        else "AXLE_FADC_SHEET_AEB_SPARE",
                        (111.4916 + 13.25 * i, 0),
                        {
                            "AXLE_FADC_SHEET_ID": f"{side2['AZgr'].iloc[i]}/{side2['AZnr'].iloc[i]}"
                            if i < len(side2)
                            else "",
                            "AXLE_FADC_SHEET_TRACK": f"{side2['Track1'].iloc[i]}{side2['FM1'].iloc[i]} / {side2['Track2'].iloc[i]}{side2['FM2'].iloc[i]}"
                            if i < len(side2)
                            else "",
                        },
                    ]
                )
            blocks.append(blockdatalist)
        return blocks


###############################################################################
# ROW A, B, C, D, E, F, G, H, J, K Strip Analysis
###############################################################################
class StripAxleSheet:
    def __init__(self, dataframe, bordervalues, sheet):
        self.MAX_ROWS = 47
        self.dataframe = dataframe
        self.bordervalues = bordervalues
        self.sheet = sheet
        self.blank_dfs = self._blank_dfs()
        self.dfs = self.build_dfs()
        self.df_split = self.split_df()
        self.blocks = self.build_blocks()
        self.next_sheet = self.sheet

    def _blank_dfs(self):
        blank_rows = ["A", "B", "C", "D", "E", "F", "G", "H", "J"]
        dfs = {}
        for r in blank_rows:
            dfs[r] = pd.DataFrame(
                [
                    {
                        "ROW": r,
                        "POS": "-",
                        "FUNCTION": "-",
                        "TYPE": "-",
                        "SHEET": "-",
                    }
                ]
            )
        dfs["K"] = pd.DataFrame(
            {
                "ROW": ["K"] * 6,
                "POS": [1, 2, 3, 4, 5, 6],
                "FUNCTION": [
                    "B60 SUPPLY 1",
                    "B60 DC-DC",
                    "N60 SUPPLY 1",
                    "N60 DC-DC",
                    "B60 SUPPLY 2",
                    "N60 SUPPLY 2",
                ],
                "TYPE": [
                    "ETA UK6-FSI/C (FUSE 6A)",
                    "ETA UK6-FSI/C (FUSE 6A)",
                    "PHOENIX UK6",
                    "PHOENIX UK6",
                    "ETA UK6-FSI/C (FUSE 6A)",
                    "PHOENIX UK6",
                ],
                "SHEET": ["N00X"] * 6,
            }
        )
        return dfs

    def build_dfs(self):
        # First format self.dataframe into list[list[pd.df(A1), pd.df(A2)]]
        # Copy from AxleFADCSheet.build_dfs
        _i = [group for _, group in self.dataframe.groupby("AZgr", sort=False)]
        grouped_df = []
        for df in _i:
            grouped_df.append(
                [
                    group.sort_values("AEB")
                    for _, group in df.groupby("FADC", sort=False)
                ]
            )
        # continue with formatting self.blank_dfs
        # self.blank_dfs["A"] example
        for fadc in grouped_df:
            side1 = fadc[0]
            side2 = fadc[1]
            self.blank_dfs[side1["FADC"].iloc[0][0]] = pd.DataFrame(
                {
                    "ROW": [side1["FADC"].iloc[0][0]] * 21,
                    "POS": [
                        "-",
                        f"{side1['FADC'].iloc[0]}",
                        "PSC",
                        "AEB1",
                        "AEB2",
                        "AEB3",
                        "AEB4",
                        "AEB5",
                        "AEB6",
                        "AEB7",
                        "AEB8",
                        f"{side2['FADC'].iloc[0]}",
                        "PSC",
                        "AEB1",
                        "AEB2",
                        "AEB3",
                        "AEB4",
                        "AEB5",
                        "AEB6",
                        "AEB7",
                        "AEB8",
                    ],
                    "FUNCTION": [
                        f"FADC AXLE COUNTER {side1['AZgr'].iloc[0]} RACK",
                        "BACKPLANE BP-PWR101-8 40TE GS01",
                        "SUPPLY BOARD PSC101 GS01",
                        "COMMS. BOARD COM-FSE",
                        "COMMS. BOARD COM-Adc",
                        "-",
                        "-",
                        "-",
                        "-",
                        "-",
                        "-",
                        "BACKPLANE BP-PWR101-8 40TE GS01",
                        "SUPPLY BOARD PSC101 GS01",
                        "COMMS. BOARD COM-FSE",
                        "-",
                        "-",
                        "-",
                        "-",
                        "-",
                        "-",
                        "-",
                    ],
                    "TYPE": [
                        "BGT07",
                        "19953",
                        "19949",
                        "112026",
                        "23152",
                        "-",
                        "-",
                        "-",
                        "-",
                        "-",
                        "-",
                        "19953",
                        "19949",
                        "26534",
                        "-",
                        "-",
                        "-",
                        "-",
                        "-",
                        "-",
                        "-",
                    ],
                    "SHEET": [
                        "R00X",
                        "-",
                        "N00X",
                        "T005",
                        "T005",
                        "-",
                        "-",
                        "-",
                        "-",
                        "-",
                        "-",
                        "-",
                        "N00X",
                        "T005",
                        "-",
                        "-",
                        "-",
                        "-",
                        "-",
                        "-",
                        "-",
                    ],
                }
            )
            for i, (_, row) in enumerate(side1.iterrows()):
                update = {
                    "FUNCTION": "EVALUATION BOARD AEB101GS11",
                    "TYPE": "110813",
                    "SHEET": row["Sheet"],
                }
                self.blank_dfs[side1["FADC"].iloc[0][0]].loc[i + 5, update.keys()] = (
                    update.values()
                )
            for i, (_, row) in enumerate(side2.iterrows()):
                update = {
                    "FUNCTION": "EVALUATION BOARD AEB101GS11",
                    "TYPE": "110813",
                    "SHEET": row["Sheet"],
                }
                self.blank_dfs[side2["FADC"].iloc[0][0]].loc[i + 14, update.keys()] = (
                    update.values()
                )

    def split_df(self):
        split_dfs = list(self.blank_dfs.values())
        index = 0
        while index + 1 < len(split_dfs):
            df_current = split_dfs[index]
            df_next = split_dfs[index + 1]
            if len(df_current) + len(df_next) <= self.MAX_ROWS:
                split_dfs[index] = pd.concat([df_current, df_next], ignore_index=True)
                split_dfs.pop(index + 1)
            else:
                index += 1
        return split_dfs

    def build_blocks(self):
        blocks = []
        for sheetindex, dataframe in enumerate(self.df_split):
            blockdatalist = []
            # Borderblock values
            self.bordervalues["BORDER_SHEET"] = f"R{self.sheet:03d}"
            blockdatalist.append(["PSP_BORDER_BLOCK", (0, 0), self.bordervalues.copy()])
            self.sheet += 1
            blockdatalist.append(
                [
                    "STRIP_ANALYSIS_TABLE_HEAD",
                    (0, 0),
                    {"TABLE_HEADING": "AZ CABINET"},
                ]
            )
            # INDEX NAME

            rows: list[str] = [row for row, _ in dataframe.groupby("ROW")]
            formated_rows: str = ", ".join(rows[:-1])
            if len(rows) > 1:
                formated_rows: str = f"{formated_rows} & {rows[-1]}"
            else:
                formated_rows = rows[0]
            blockdatalist.append(
                [
                    "BORDER_INDEX_NAME",
                    (0, 0),
                    {
                        "BORDER_INDEX_NAME": f"AZ CABINET - ROW {formated_rows} STRIP ANALYSIS"
                    },
                ]
            )
            for i, df_row in dataframe.iterrows():
                blockdatalist.append(
                    [
                        "STRIP_ANALYSIS_TABLE_ROW",
                        (0, -5 * i),
                        {
                            "A1": df_row["ROW"],
                            "A2": df_row["POS"],
                            "A3": df_row["FUNCTION"],
                            "A4": df_row["TYPE"],
                            "A5": df_row["SHEET"],
                        },
                    ]
                )
            blocks.append(blockdatalist)
        return blocks


###############################################################################
# Row L analysis
###############################################################################
class AxleLSheet:
    def __init__(self, dataframe, bordervalues, sheet):
        self.MAX = 14
        self.MAX_PER_SHEET = 8
        self.dataframe = dataframe
        self.bordervalues = bordervalues
        self.sheet = sheet
        self.df_split = self.split_df()
        self.blocks = self.build_blocks()
        self.next_sheet = self.sheet

    def split_df(self):
        df_split = [
            group
            for _, group in self.dataframe.groupby(
                self.dataframe.index // self.MAX_PER_SHEET
            )
        ]
        return df_split

    def build_blocks(self):
        # Iterate through list to isolate dataframe to a sheet
        blocks = []
        prevpos = 1
        for sheetindex, dataframe in enumerate(self.df_split, start=1):
            blockdatalist = []
            self.bordervalues["BORDER_SHEET"] = f"R{self.sheet:03d}"
            blockdatalist.append(["PSP_BORDER_BLOCK", (0, 0), self.bordervalues.copy()])
            self.sheet += 1
            blockdatalist.append(
                [
                    "IDF_BASE",
                    (0, 0),
                    {
                        "TABLE_HEAD": "AXLE COUNTER CABINET",
                    },
                ]
            )
            blockdatalist.append(
                [
                    "BORDER_INDEX_NAME",
                    (0, 0),
                    {
                        "BORDER_INDEX_NAME": f"AZ CABINET - ROW L STRIP ANALYSIS ({sheetindex} OF {len(self.df_split)})"
                    },
                ]
            )
            for i, (_, row) in enumerate(dataframe.iterrows()):
                blockdatalist.append(
                    [
                        "AXLE_L_STRIP_TABLE",
                        (0, 0 - 25 * i),
                        {
                            "A1_1": "L",
                            "A2_1": prevpos,
                            "A3_1": f"{row['AZgr']}/{row['AZnr']} - SYS1",
                            "A3_2": f"{row['AZgr']}/{row['AZnr']} - SYS2",
                            "A3_3": f"{row['AZgr']}/{row['AZnr']} - VCC",
                            "A3_4": f"{row['AZgr']}/{row['AZnr']} - GND",
                            "A3_5": f"{row['AZgr']}/{row['AZnr']} - EARTH",
                            **{f"A4_{e}": row["Sheet"] for e in range(1, 6)},
                        },
                    ]
                )
                prevpos += 1
            blocks.append(blockdatalist)
        return blocks


###############################################################################
# Row M analysis
###############################################################################
class AxleMSheet:
    def __init__(self, dataframe, bordervalues, sheet):
        self.MAX = 14
        self.MAX_PER_SHEET = 10
        self.dataframe = dataframe
        self.bordervalues = bordervalues
        self.sheet = sheet
        self.df_split = self.split_df()
        self.blocks = self.build_blocks()
        self.next_sheet = self.sheet

    def split_df(self):
        df_split = [
            group
            for _, group in self.dataframe.groupby(
                self.dataframe.index // self.MAX_PER_SHEET
            )
        ]
        return df_split

    def build_blocks(self):
        # Iterate through list to isolate dataframe to a sheet
        blocks = []
        prevpos = 1600
        for sheetindex, dataframe in enumerate(self.df_split, start=1):
            blockdatalist = []
            self.bordervalues["BORDER_SHEET"] = f"R{self.sheet:03d}"
            blockdatalist.append(["PSP_BORDER_BLOCK", (0, 0), self.bordervalues.copy()])
            self.sheet += 1
            blockdatalist.append(
                [
                    "AXLE_STRIP_ANALYSIS_TABLE_HEAD",
                    (0, 0),
                    {
                        "TABLE_HEAD": "AXLE COUNTER CABINET",
                    },
                ]
            )
            blockdatalist.append(
                [
                    "BORDER_INDEX_NAME",
                    (0, 0),
                    {
                        "BORDER_INDEX_NAME": f"AZ CABINET - ROW M STRIP ANALYSIS ({sheetindex} OF {len(self.df_split)})"
                    },
                ]
            )
            for i, (_, row) in enumerate(dataframe.iterrows()):
                blockdatalist.append(
                    [
                        "AXLE_STRIP_ANALYSIS_TABLE",
                        (0, 0 - 20 * i),
                        {
                            **{f"A1_{e}": "M" for e in range(1, 5)},
                            **{f"A2_{e}": prevpos + e for e in range(1, 5)},
                            "A3_1": f"{row['AZgr']}/{row['AZnr']} - SYS1",
                            "A3_2": f"{row['AZgr']}/{row['AZnr']} - SYS2",
                            "A3_3": f"{row['AZgr']}/{row['AZnr']} - VCC",
                            "A3_4": f"{row['AZgr']}/{row['AZnr']} - GND",
                            **{f"A4_{e}": "TERMINALS" for e in range(1, 5)},
                            **{f"A5_{e}": row["Sheet"] for e in range(1, 5)},
                        },
                    ]
                )
                prevpos += 4
            blocks.append(blockdatalist)
        return blocks


#############################################################################
# Used to create the drawing files from the Rsheets(
#############################################################################
class DrawingRenderer:
    def __init__(self, template, output_dir: Path):
        self.template = ez.readfile(template)
        self.output_dir = output_dir

    def render_sheets(self, blocks):
        self.output_dir = Path(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        for index, sheetblocks in enumerate(blocks):
            drawing = copy.deepcopy(self.template)
            psp = drawing.paperspace()
            msp = drawing.modelspace()
            for block in sheetblocks:
                # block contains (block_str: str, placement:(int,int), attribute_defs: dict)
                if "PSP" in block[0]:
                    psp.add_auto_blockref(*block)
                else:
                    msp.add_auto_blockref(*block)
            while insert := len(msp.query("INSERT")):
                for insert in list(msp.query("INSERT")):
                    insert.explode()

            while insert := len(psp.query("INSERT")):
                for insert in list(psp.query("INSERT")):
                    insert.explode()
            output_file = (
                self.output_dir
                / f"{sheetblocks[0][-1]['DocDate']}-{sheetblocks[0][-1]['BORDER_DOC_NAME']}-{sheetblocks[0][-1]['BORDER_SHEET']}-REV-{sheetblocks[0][-1]['BORDER_REV']}.dxf"
            )
            drawing.saveas(output_file)


if __name__ == "__main__":
    s = time.perf_counter()
    r_section = RSection(Path("templates/autobook.xlsx"), 2)
    e = time.perf_counter()
    print(f"Rsection dataframes generated: {e - s:0.2f}s")

    r_subsections = [
        r_section.idf_signal,
        r_section.idf_points,
        r_section.op_signal,
        r_section.op_point,
        r_section.op_counter,
        r_section.power,
        r_section.io,
        r_section.points,
        r_section.signals,
        r_section.strip,
        r_section.fadc,
        r_section.axlestrip,
        r_section.lstrip,
        r_section.mstrip,
    ]
    s = time.perf_counter()
    renderer = DrawingRenderer(str("templates/Roptemplate.dxf"), Path("../out/"))
    e = time.perf_counter()
    print(f"DrawingRenderer set: {e - s:0.2f}s")

    for i in r_subsections:
        s = time.perf_counter()
        renderer.render_sheets(i.blocks)
        e = time.perf_counter()
        print(f"Drawing build time: {e - s:0.2f}s")
