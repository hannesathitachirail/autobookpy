from itertools import groupby

import ezdxf as ez
import pandas as pd
import copy
import numpy as np


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
    def __init__(self, excel_file):
        self.MAX_ROWS = 40
        self.dataframe = pd.read_excel(excel_file, sheet_name=["Border", "D", "E", "F"])
        self.idf_signal = IDFSignalsSheet(
            self.dataframe["D"], self.bordervalues, 2
        )  # To be updated
        self.idf_points = IDFPointsSheet(
            self.dataframe["E"], self.bordervalues, 2
        )  # To be updated
        self.op_signal = OPSignalsSheet(self.dataframe["D"], self.bordervalues)
        self.op_points = OPPointsSheet(
            self.dataframe["E"], self.bordervalues, 2
        )  # To be updated
        self.op_counter = OPCounterSheet(
            self.dataframe["F"], self.bordervalues, 2
        )  # To be updated

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
        self.MAX_PER_SHEET = 5
        self.dataframe = dataframe
        self.bordervalues = bordervalues
        self.sheet = sheet
        self.df = self.build_df()
        self.df_split = self.split_df()
        self.blocks = self.build_blocks()

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
            self.bordervalues["BORDER_SHEET"] = f"R{self.sheet + sheetindex - 1:03d}"
            blockdatalist.append(["PSP_BORDER_BLOCK", (0, 0), self.bordervalues.copy()])
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
            blockdatalist.append(["PSP_BORDER_BLOCK", (0, 0), self.bordervalues])
            blockdatalist.append(
                [
                    "IDF_BASE",
                    (0, 0),
                    {
                        "TABLE_HEAD": f"OP 11 - {dataframe['IDFRow'].iloc[0][0]}",
                    },
                ]
            )
            blockdatalist.append(
                [
                    "BORDER_INDEX_NAME",
                    (0, 0),
                    {
                        "BORDER_INDEX_NAME": f"OP 11 - {dataframe['IDFRow'].iloc[0][0]} STRIP ANALYSIS ({sheetindex} OF {len(self.df_split)})"
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
    def __init__(self, dataframe, bordervalues):
        self.MAX_ROWS = 40
        self.dataframe = dataframe
        self.bordervalues = bordervalues
        self.df = self.build_df()
        self.df_split = self.split_df()
        self.blocks = self.build_blocks()

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
            blockdatalist.append(["PSP_BORDER_BLOCK", (0, 0), self.bordervalues])
            blockdatalist.append(
                [
                    "OP_BASE",
                    (0, 0),
                    {
                        "TABLE_HEAD": "OP 11 - D",
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
        self.df_split = self.split_df()
        self.blocks = self.build_blocks()

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
        for sheetindex, dataframe in enumerate(self.df_split, start=1):
            blockdatalist = []
            blockdatalist.append(["PSP_BORDER_BLOCK", (0, 0), self.bordervalues])
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
                        "BORDER_INDEX_NAME": f"OP 11 - {dataframe['IDFRow'].iloc[0][0]} STRIP ANALYSIS ({sheetindex} OF {len(self.df_split)})"
                    },
                ]
            )
            for i, (_, row) in enumerate(dataframe.iterrows()):
                blockdatalist.append(
                    [
                        "OPPOINT_TABLE",
                        (0, 0 - 20 * i),
                        {
                            **{f"A1_{e}": row["OPRow"][0] for e in range(1, 5)},
                            **{f"A1_{e}": row["OPRow"][0] for e in range(1, 5)},
                            "A2_1": 1 + 4 * i,
                            "A2_2": 2 + 4 * i,
                            "A2_3": 3 + 4 * i,
                            "A2_4": 4 + 4 * i,
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
            blocks.append(blockdatalist)
        return blocks


#########################
# Counters OP sheets
# Max 40 terminals per sheet
########################
class OPCounterSheet:
    def __init__(self, dataframe, bordervalues, sheet):
        self.MAX = 14
        self.MAX_PER_SHEET = 10
        self.dataframe = dataframe
        self.bordervalues = bordervalues
        self.sheet = sheet
        self.df = self.build_df()
        self.df_split = self.split_df()
        self.blocks = self.build_blocks()

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
                for i in range(q - qn):

                breakpoint()

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
        for sheetindex, dataframe in enumerate(self.df_split, start=1):
            blockdatalist = []
            self.bordervalues["BORDER_SHEET"] = f"R{self.sheet + sheetindex - 1:03d}"
            blockdatalist.append(["PSP_BORDER_BLOCK", (0, 0), self.bordervalues])
            blockdatalist.append(
                [
                    "OP_BASE",
                    (0, 0),
                    {
                        "TABLE_HEAD": f"OP 11 - {dataframe['OP'].iloc[0][0][-1]}",
                    },
                ]
            )
            blockdatalist.append(
                [
                    "BORDER_INDEX_NAME",
                    (0, 0),
                    {
                        "BORDER_INDEX_NAME": f"OP 11 - {dataframe['OP'].iloc[0][0][-1]} STRIP ANALYSIS ({sheetindex} OF {len(self.df_split)})"
                    },
                ]
            )
            for i, (_, row) in enumerate(dataframe.iterrows()):
                blockdatalist.append(
                    [
                        "OPPOINT_TABLE",
                        (0, 0 - 20 * i),
                        {
                            **{f"A1_{e}": row["OPRow"][0] for e in range(1, 5)},
                            **{f"A1_{e}": row["OPRow"][0] for e in range(1, 5)},
                            "A2_1": 1 + 4 * i,
                            "A2_2": 2 + 4 * i,
                            "A2_3": 3 + 4 * i,
                            "A2_4": 4 + 4 * i,
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
            blocks.append(blockdatalist)
        return blocks


#############################################################################
# Used to create the drawing files from the Rsheets(
#############################################################################
class DrawingRenderer:
    def __init__(self, blocks, template):
        self.block_list = blocks
        self.template = ez.readfile(template)

    def render_sheets(self):
        for index, sheetblocks in enumerate(self.block_list):
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
            drawing.saveas(f"R00{index}.dxf")


if __name__ == "__main__":
    r_section = RSection("./autobook.xlsx")

    Renderer = DrawingRenderer(
        r_section.op_signal.blocks, "./templates/Roptemplate.dxf"
    )
    Renderer.render_sheets()
