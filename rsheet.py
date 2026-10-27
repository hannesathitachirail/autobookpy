import pandas as pd


#############################################################################
# This class is used to create an Rsection object that takes the spreadsheet
# and creates one big dataframe(not split) containing all the rows that would
# be needed for the seperate Rsheets object
#
# The final output would be a list of sheets(dataframes) split into 40 row
# dataframes. This is used to create the Rsheet objects for every sheet(dataframes)
#############################################################################
class RSection:
    MAX_ROWS = 40

    def __init__(self, dataframe: pd.DataFrame):
        self.dataframe = dataframe

    def build_op_df(self):
        # Start by reordering the dataframe.
        # Create list of dataframes grouped by "CableAppCase" and sorted by "AppCaseOrder"
        # for appcases group and "CableBox" for straight fed
        # pd.concat is used to merge the list of dataframes into one dataframe
        dfs = [
            group.sort_values("AppCaseOrder")
            if not pd.isna(group["CableAppCase"].iloc[0])
            else group.sort_values(
                "CableBox", key=lambda x: x.str.split(".").str[-1].astype(int)
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
            "s": ("(S)UG", "(S)UGCX"),
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
                    # CORE list
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
        self.OPdf = pd.concat(tables, ignore_index=True)
        self.OPdf["POS"] = range(1, len(formatteddf) + 1)
        return self.OPdf


#############################################################################
# From the Rsection class we make the different Rsheet ojects that takes the
#   - Dataframe containing the data for every rows
# Determines what blocks will be needed aswell as the values(attributes) for
# the blocks
#############################################################################
class RSheet:
    pass


#############################################################################
# Used to create the drawing files from the Rsheets
#############################################################################
class DrawingRenderer:
    pass


if __name__ == "__main__":
    df = pd.read_excel("./autobook.xlsx", "D")
    rsection = RSection(df)
    rsection.build_op_df()
