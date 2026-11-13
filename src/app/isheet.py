import ezdxf as ez
import pandas as pd
import copy
from pathlib import Path

bordernames: dict = {
    "D": ("D - SIGNALS CIRCUITRY INDEX", "SIGNALS CIRCUITRY INDEX", "SignalName"),
    "E": ("E - POINTS CIRCUITRY INDEX", "POINTS CIRCUITRY INDEX", "PointName"),
    "F": (
        "F - AXLE COUNTERS CIRCUTIRY INDEX",
        "AXLE COUNTERS CIRCUITRY INDEX",
        "Sheet",
    ),
}


def updateDict(data: pd.DataFrame):
    data = data.astype(str)  # Convert all dataframe values to strings
    data["LOC"] = data["LOC"].astype(str).str.zfill(2)
    data["Bordername"] = data["Sheet"].str[0]
    sheetsDict = []
    for row in data.to_dict(orient="records"):
        sheetsDict.append(
            {
                # General Dictionary
                "Sheet": row["Sheet"],
                "DocDate": row["DocDate"],
                # Base text
                "TITLE": bordernames[f"{row['Bordername']}"][0],
                "BORDER_NAME": bordernames[f"{row['Bordername']}"][1],
                # PSP_BORDER_BLOCk
                "BORDER_STATION_L1": f"{row['Station']} {row['Room']}"
                if row["Room"] != "nan"
                else f"{row['Station']}",
                "BORDER_STATION_L2": f"({row['Sta']} {row['Room']})"
                if row["Room"] != "nan"
                else f"({row['Sta']})",
                "BORDER_SHEET": f"{row['Sheet'][0]}000",
                "BORDER_CSE": row["CSE"],
                "BORDER_STATION_CODE": row["Code"],
                "BORDER_DATE": row["Date"],
                "BORDER_DOC_NAME": row["Doc"],
                "BORDER_REV": row["Rev"],
                "INDEX_NAME": bordernames[f"{row['Bordername']}"][0][4:],
            }
        )
    return sheetsDict


def get_blocks(sheet, df: pd.DataFrame):
    required_blocks = []
    # General
    required_blocks.append(("BASE_TEXT", (0, 0), {}))
    required_blocks.append(("PSP_BORDER_BLOCK", (0, 0), {}))
    required_blocks.append(("INDEX_NAME", (0, 0), {}))
    for index, row in df.iterrows():
        tablevalues: dict = {
            "A1": f"{row['Sheet']}",
            "A2": row["SheetName"]
            if "F" not in row["SheetName"]
            else f"{row['AZgr']}/{row['AZnr']} - {row['Track1']} / {row['Track2']}",
            "A3": f"{row['Rev']}",
            "A4": f"{row['LastDateRevised']}",
            "A5": f"{row['Modification']}",
        }
        required_blocks.append(("TABLE_5_1", (0, 238.2944 - 7 * index), tablevalues))
    return required_blocks


def generatesheets(
    templatefile: Path, excelsheet: Path, section: str, output_dir: Path
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    dataframe = pd.read_excel(excelsheet, section)
    dataframe["SheetName"] = dataframe[bordernames[section][2]]
    dataframes = pd.read_excel(
        excelsheet,
        sheet_name=[section, "Border"],
    )

    dataframe = dataframes[section]
    border_df = dataframes["Border"]
    dataframe = dataframes[section].merge(
        border_df,
        how="cross",
    )
    dataframe["SheetName"] = dataframe[bordernames[section][2]]
    sheetsDict = updateDict(dataframe)
    template = ez.readfile(templatefile)
    for sheet in sheetsDict:
        newdrawing = copy.deepcopy(template)
        msp = newdrawing.modelspace()
        psp = newdrawing.paperspace()
        blocks = get_blocks(sheet, dataframe)
        for block, insert, tablevalues in blocks:
            if "PSP" in block:
                psp.add_auto_blockref(block, insert, sheet)
            else:
                msp.add_auto_blockref(block, insert, sheet | tablevalues)
        # Convert every block ref to seperate objects
        while insert := len(msp.query("INSERT")):
            for insert in list(msp.query("INSERT")):
                insert.explode()
        while insert := len(psp.query("INSERT")):
            for insert in list(psp.query("INSERT")):
                insert.explode()
        output_file = (
            output_dir
            / f"{sheet['DocDate']}-{sheet['BORDER_DOC_NAME']}-{sheet['Sheet'][0:-1]}0-REV-{sheet['BORDER_REV']}.dxf"
        )
        newdrawing.saveas(output_file)
    # odafc.export_dwg(
    #    newdrawing,
    #    f"./out/{sheet['DocDate']}-{sheet['BORDER_DOC_NAME']}-{sheet['Sheet']}-REV-{sheet['BORDER_REV']}.dwg",
    #    version="R2018",
    # )


if __name__ == "__main__":
    sections = ["D", "E", "F"]
    for s in sections:
        generatesheets(
            Path("../templates/Itemplate.dxf"),
            Path("../autobook.xlsx"),
            s,
            Path("../out/"),
        )
