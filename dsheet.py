import ezdxf as ez
from ezdxf.addons import odafc
import pandas as pd
import copy
import time
import numpy as np

excelsheet = "./autobook.xlsx"

output = "./out/"


def updateDict(data: pd.DataFrame):
    data = data.fillna("")
    data["Dir"] = data["Dir"].astype(str) + "   "
    data["Aspect"] = data["Aspect"].astype(str) + "   "
    data["isfirstscm"] = ~data["SCM"].duplicated()
    data["OtherSheet"] = data.groupby("SCM")["Sheet"].transform(
        lambda x: x.iloc[::-1].values if len(x) == 2 else ""
    )
    data["OtherSig"] = data.groupby("SCM")["SignalName"].transform(
        lambda x: x.iloc[::-1].values if len(x) == 2 else ""
    )
    data["OtherPowerSheet"] = data.groupby("SCM")["PowerSheet"].transform(
        lambda x: x.iloc[::-1].values if len(x) == 2 else ""
    )
    OtherAsp = data.groupby("SCM")["Aspect"].transform(
        lambda x: x.iloc[::-1].values if len(x) == 2 else ""
    )
    OtherDir = data.groupby("SCM")["Dir"].transform(
        lambda x: x.iloc[::-1].values if len(x) == 2 else ""
    )
    data["OtherAspDir"] = (
        OtherAsp.str.strip().str.len().fillna(0)
        + OtherDir.str.strip().str.len().fillna(0)
    ).astype(int)
    sheetsDict = []
    for row in data.to_dict(orient="records"):
        sheetsDict.append(
            {
                # General
                "Sheet": row["Sheet"],
                "DocDate": row["DocDate"],
                "OtherSheet": row["OtherSheet"],
                "ASPECT": row["Aspect"],
                "ASPECTFLASHING": row["AspectFlashing"],
                "DIR": row["Dir"],
                "SCM": row["SCM"],
                "ISFIRSTSCM": row["isfirstscm"],
                "FIRSTSHEET": row["Sheet"] if row["isfirstscm"] else row["OtherSheet"],
                "SECONDSHEET": row["Sheet"]
                if not row["isfirstscm"]
                else row["OtherSheet"],
                "OTHERASPDIR": row["OtherAspDir"],
                # BASE_TEXt values
                "ROOM_TYPE": row["RoomType"],
                "LOC": f"RSS LOC-{row['LOC']} CABINET",
                "POWER_INPUT": row["SCM"],
                # Border block values
                "BORDER_STATION_L1": f"{row['Station']} {row['Room']}"
                if row["Room"] != ""
                else f"{row['Station']}",
                "BORDER_STATION_L2": f"({row['Sta']} {row['Room']})"
                if row["Room"] != ""
                else f"({row['Sta']})",
                "BORDER_NAME": f"{row['SignalName']}",
                "BORDER_SHEET": row["Sheet"],
                "BORDER_CSE": row["CSE"],
                "BORDER_STATION_CODE": row["Code"],
                "BORDER_DATE": row["Date"],
                "BORDER_DOC_NAME": row["Doc"],
                "BORDER_REV": row["Rev"],
                # Power
                "DIST_SHEET": row["PowerSheet"],
                "OTHER_DIST_SHEET": row["OtherPowerSheet"],
                "PowerSheet": row["PowerSheet"],
                "OtherPowerSheet": row["OtherPowerSheet"],
                # Signal
                "SIG_NAME": f"{row['SignalName']}",
                "DB_SIG_NAME": f"DB {row['SignalName']}",
                # SignalRef
                "SIG_REF_L1": f"{row['OtherSig']}:",
                "SIG_REF_L2": f"SHEET {row['OtherSheet']}",
                # IDs
                "IDF": f"IDF {row['IDFRack']} - {row['IDFRow']}",
                "IDF2": f"IDF {row['IDFRack2']} - {row['IDFRow2']}",
                "IDFRow2": row["IDFRow2"],
                # Main OP
                "OP": f"OP {row['OPRack']} - {row['OPRow']}",
                **{f"OP{i + 1}": f"{row['OPnr'] + i}" for i in range(12)},
                # Cable Boxes
                "CABLEBOX_L1": f"{row['CableBox']}",
                "CABLEBOX_L2": f"{row['CableBoxQ']}",
                **{
                    f"CABLEBOX{i}": f"{e}a"
                    for i, e in zip(range(1, 14, 2), range(1, 7))
                },
                **{
                    f"CABLEBOX{i}": f"{e}b"
                    for i, e in zip(range(2, 15, 2), range(1, 7))
                },
                # App case
                "CABLEAPPCASE_L1": f"{row['CableAppCase']}",
                "CABLEAPPCASE_L2": f"{row['CableAppCaseQ']}",
                "APPCASE_NAME": f"{row['CableAppCase'][-7:-2]}",
                **{
                    f"APPCASE{i}": f"{int(row['AppCaseNr'] or 0) + i - 1}"
                    for i in range(1, 13)
                },
                **{
                    f"CABLEAPPCASE{i}": f"{(int(row['AppCaseNr'] or 0) + i) // 2}a"
                    for i in range(1, 32, 2)
                },
                **{
                    f"CABLEAPPCASE{i + 1}": f"{(int(row['AppCaseNr'] or 0) + i) // 2}b"
                    for i in range(1, 32, 2)
                },
                # Direction Definitions
                "ASPECTD1_1": f"({'↑' if row['Dir'][0] == 'S' else row['Dir'][0]})UG",
                "ASPECTD1_2": f"({'↑' if row['Dir'][0] == 'S' else row['Dir'][0]})UGCX",
                "ASPECTD2_1": f"({'↑' if row['Dir'][1] == 'S' else row['Dir'][1]})UG",
                "ASPECTD2_2": f"({'↑' if row['Dir'][1] == 'S' else row['Dir'][1]})UGCX",
                "ASPECTD3_1": f"({'↑' if row['Dir'][2] == 'S' else row['Dir'][2]})UG",
                "ASPECTD3_2": f"({'↑' if row['Dir'][2] == 'S' else row['Dir'][2]})UGCX",
                # Aspect Definitions
                "ASPECT1_NAME_L1": f"{'GREEN' if row['Aspect'][0] == 'G' else 'YELLOW' if row['Aspect'][0] == 'H' else 'RED' if row['Aspect'][0] == 'R' else ''}",
                "ASPECT2_NAME_L1": f"{'GREEN' if row['Aspect'][1] == 'G' else 'YELLOW' if row['Aspect'][1] == 'H' else 'RED' if row['Aspect'][1] == 'R' else ''}",
                "ASPECT3_NAME_L1": f"{'GREEN' if row['Aspect'][2] == 'G' else 'YELLOW' if row['Aspect'][2] == 'H' else 'RED' if row['Aspect'][2] == 'R' else ''}",
                "ASPECT1_NAME_L2": "LED",
                "ASPECT2_NAME_L2": "LED",
                "ASPECT3_NAME_L2": "LED",
                "ASPECT1_1": f"{row['Aspect'][0]}G",
                "ASPECT1_2": f"{row['Aspect'][0]}GCX",
                "ASPECT2_1": f"{row['Aspect'][1]}G",
                "ASPECT2_2": f"{row['Aspect'][1]}GCX",
                "ASPECT3_1": f"{row['Aspect'][2]}G",
                "ASPECT3_2": f"{row['Aspect'][2]}GCX",
            }
        )
        if row["isfirstscm"]:
            sheetsDict[-1].update(
                **{
                    f"SCMT{i}": f"C{e}"
                    for i, e in zip(range(1, 21, 2), range(14, 33, 2))
                },
                **{
                    f"SCMT{i}": f"E{e}"
                    for i, e in zip(range(2, 21, 2), range(14, 33, 2))
                },
                **{
                    f"SCMT{i}_REF": f"C{e}"
                    for i, e in zip(range(1, 21, 2), range(24, 33, 2))
                },
                **{
                    f"SCMT{i}_REF": f"E{e}"
                    for i, e in zip(range(2, 21, 2), range(24, 33, 2))
                },
                # OUT values
                **{f"OUT{i}": f"OUT{(i - 1) // 2}_L" for i in range(1, 33, 2)},
                **{f"OUT{i}": f"OUT{(i - 1) // 2}_N" for i in range(2, 33, 2)},
            )
        else:
            sheetsDict[-1].update(
                **{
                    f"SCMT{i}": f"C{e}"
                    for i, e in zip(range(1, 21, 2), range(24, 33, 2))
                },
                **{
                    f"SCMT{i}": f"E{e}"
                    for i, e in zip(range(2, 21, 2), range(24, 33, 2))
                },
                **{
                    f"SCMT{i}_REF": f"C{e}"
                    for i, e in zip(range(1, 21, 2), range(14, 33, 2))
                },
                **{
                    f"SCMT{i}_REF": f"E{e}"
                    for i, e in zip(range(2, 21, 2), range(14, 33, 2))
                },
                # OUT values
                **{f"OUT{i}": f"OUT{(i + 9) // 2}_L" for i in range(1, 33, 2)},
                **{f"OUT{i}": f"OUT{(i + 9) // 2}_N" for i in range(2, 33, 2)},
            )
    return sheetsDict


# When given signal aspect and direction (GHR), (LSR) returns list of blocks that need to be added
def get_blocks(sheet, df: pd.DataFrame):
    aspect_count: int = len(sheet["ASPECT"].strip())
    dir_count: int = len(sheet["DIR"].strip())
    required_blocks = []
    # General
    required_blocks.append(("BASE_TEXT", (0, 0)))
    # Add border blocks
    required_blocks.append(("PSP_BORDER_BLOCK", (0, 0)))
    # Power block
    if sheet["OtherSheet"] == "":
        if len(sheet["DIR"]) == 0:
            required_blocks.append(("POWER_1A_1SIG", (0, 0)))
        else:
            required_blocks.append(("POWER_2A_1SIG", (0, 0)))
    else:
        if sheet["ISFIRSTSCM"]:
            required_blocks.append(("POWER_TERMINAL_TOP", (0, 0)))
            required_blocks.append(("POWER_REF_1", (53.6311, 216.6655)))
            required_blocks.append(("POWER_REF_1_1", (53.6311, 121.0856)))
            required_blocks.append(("POWER_TERMINAL_BOTTOM_DASHED", (0, -55.5799)))
        else:
            required_blocks.append(("POWER_TERMINAL_TOP_DASHED", (0, 0)))
            required_blocks.append(("POWER_REF_1_1", (53.6311, 216.6655)))
            required_blocks.append(("POWER_REF_1", (53.6311, 121.0856)))
            required_blocks.append(("POWER_TERMINAL_BOTTOM", (0, -55.5799)))

    # Find what block is needed for the Signalcable
    if aspect_count + dir_count <= 3 and pd.isna(sheet["SECONDSHEET"]):
        required_blocks.append(("SIGNALCABLE_SHORT", (106.3074, 216.6655)))
    else:
        required_blocks.append(("SIGNALCABLE_LONG", (106.3074, 216.6655)))

    # Find what signal block is needed
    required_blocks.append(
        (
            f"{aspect_count}ASPECT_{dir_count}DIR_1SCM",
            (75.4413, 216.6655) if sheet["ISFIRSTSCM"] else (75.4413, 121.0856),
        )
    )
    # SIGNAL REF block
    if sheet["OTHERASPDIR"] > 0:
        required_blocks.append(
            (
                f"SIGREF_{sheet['OTHERASPDIR']}",
                (75.4413, 121.0856) if sheet["ISFIRSTSCM"] else (75.4413, 216.6655),
            )
        )
    # Find what appcase block is needed
    if sheet["CABLEAPPCASE_L1"] != "":
        if aspect_count + dir_count == 4:
            required_blocks.append(
                (
                    "4ASPECT_0DIR_APPCASE",
                    (218.9083, 216.6655)
                    if sheet["ISFIRSTSCM"]
                    else (218.9083, 121.0856),
                )
            )
        else:
            required_blocks.append(
                (
                    f"{aspect_count}ASPECT_{dir_count}DIR_APPCASE",
                    (218.9083, 216.6655)
                    if sheet["ISFIRSTSCM"]
                    else (218.9083, 121.0856),
                )
            )
    # SIGNALMODEL
    required_blocks.append(("PSP_SIGNALBASE_NORMAL", (413.1609, 23.6633)))
    if sheet["ASPECTFLASHING"] == "":
        required_blocks.append(("PSP_SIGNALHEAD2_R", (413.1609, 18.6633)))
    else:
        required_blocks.append(
            (
                f"PSP_SIGNALHEAD1_{sheet['ASPECTFLASHING']}",
                (413.1609, 23.6633),
            )
        )
        required_blocks.append(
            (
                f"PSP_SIGNALHEAD2_{sheet['ASPECT'].strip()}",
                (413.1609, 23.6633),
            )
        )
        if sheet["DIR"].strip() != "":
            required_blocks.append(
                (
                    f"PSP_SIGNALDIR_{sheet['DIR'].strip()}",
                    (413.1609, 23.6633),
                )
            )
    return required_blocks


def generatesheets(
    templatefile: str,
    excelsheet,
):
    dataframe = pd.read_excel(excelsheet, "D")
    sheetsDict = updateDict(dataframe)
    template = ez.readfile(templatefile)

    for sheet in sheetsDict:
        newdrawing = copy.deepcopy(template)
        msp = newdrawing.modelspace()
        psp = newdrawing.paperspace()
        blocks = get_blocks(sheet, dataframe)
        for block, insert in blocks:
            if "PSP" in block:
                psp.add_auto_blockref(block, insert, sheet)
            else:
                msp.add_auto_blockref(block, insert, sheet)
        # Convert every block ref to seperate objects
        while insert := len(msp.query("INSERT")):
            for insert in list(msp.query("INSERT")):
                insert.explode()

        while insert := len(psp.query("INSERT")):
            for insert in list(psp.query("INSERT")):
                insert.explode()
        newdrawing.saveas(
            f"{output}{sheet['DocDate']}-{sheet['BORDER_DOC_NAME']}-{sheet['Sheet']}-REV-{sheet['BORDER_REV']}.dxf"
        )
        # odafc.export_dwg(
        #    newdrawing,
        #    f"./out/{sheet['DocDate']}-{sheet['BORDER_DOC_NAME']}-{sheet['Sheet']}-REV-{sheet['BORDER_REV']}.dwg",
        #    version="R2018",
        # )


if __name__ == "__main__":
    start = time.perf_counter()
    generatesheets("./templates/Dtemplate.dxf", excelsheet)
    end = time.perf_counter()
    print(f"Elapse time: {end - start:.0f}")
