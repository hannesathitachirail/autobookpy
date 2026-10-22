import ezdxf as ez
from ezdxf.addons import odafc
import pandas as pd
import copy
import time
import numpy as np

excelsheet = "./autobook.xlsx"
output = "./out/"
df = pd.read_excel(excelsheet, "E")


def updateDict(data: pd.DataFrame):
    data = data.astype(str)  # Convert all dataframe values to strings
    sheetsDict = []
    for row in data.to_dict(orient="records"):
        sheetsDict.append(
            {
                # General
                "Sheet": row["Sheet"],
                "DocDate": row["DocDate"],
                "PointRep": f"{row['PointRep'][-3:]}",
                # Border / Title Block
                "BORDER_CSE": f"{row['CSE']}",
                "BORDER_DATE": f"{row['Date']}",
                "BORDER_DOC_NAME": f"{row['Doc']}",
                "BORDER_NAME": f"{row['PointName']}",
                "BORDER_REV": f"{row['Rev']}",
                "BORDER_SHEET": f"{row['Sheet']}",
                "BORDER_STATION_L1": f"{row['Station']} {row['Room']}",
                "BORDER_STATION_L2": f"({row['Sta']} {row['Room']})",
                "BORDER_STATION_CODE": f"{row['Code']}",
                # Power
                "PCM": f"{row['PCM']}",
                "POWER_INPUT": f"{row['PCM']}",
                "POWER_SHEET": f"{row['PowerSheet']}",
                # Cable Box
                "CABLEBOX_L1": f"{row['CableBox']}",
                "CABLEBOX_L2": "4c",
                # Operations
                "OP": f"OP {row['OPRack']} - {row['OPRow']}",
                "OPNR1": f"{row['OPnr']}",
                "OPNR2": f"{int(row['OPnr']) + 1}",
                "OPNR3": f"{int(row['OPnr']) + 2}",
                "OPNR4": f"{int(row['OPnr']) + 3}",
                # Identification
                "IDF": f"IDF {row['IDFRack']} - {row['IDFRow'][0]}",
                "IDFROW1": f"{row['IDFRow']}",
                "IDFROW2": f"{row['IDFRow'][0]}{int(row['IDFRow'][1:]) + 1}",
                "POINTNAME": f"{row['PointName']}",
                "LOC": f"RSS LOC-{row['LOC']} CABINET",
                "ROOM_TYPE": f"{row['RoomType']}",
            }
        )
    return sheetsDict


def get_blocks(sheet, df: pd.DataFrame):
    required_blocks = []
    # General
    required_blocks.append(("BASE_TEXT", (0, 0)))
    required_blocks.append(("PSP_BORDER_BLOCK", (0, 0)))
    required_blocks.append((f"PSP_POINTREP_{sheet['PointRep']}", (0, 0)))
    return required_blocks


def generatesheets(
    templatefile: str,
    excelsheet,
):
    dataframe = pd.read_excel(excelsheet, "E")
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
    generatesheets("./templates/Etemplate.dxf", "./autobook.xlsx")
    end = time.perf_counter()
    print(f"Elapse time: {end - start:.0f}")
