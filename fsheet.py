import ezdxf as ez
from ezdxf.addons import odafc
import pandas as pd
import copy
import time

df = pd.read_excel("./autobook.xlsx", "F")
output = "./out/"


def updateDict(data: pd.DataFrame):
    data = data.astype(str)  # Convert all dataframe values to strings
    sheetsDict = []
    for row in data.to_dict(orient="records"):
        sheetsDict.append(
            {
                # General Dictionary
                "Sheet": row["Sheet"],
                "isAppcase": pd.isna(row["Q"]),
                "DocDate": row["DocDate"],
                # Dictionary section mainly used for model block
                "ROOM_TYPE": row["RoomType"].upper(),
                "FADC": row["FADC"][0],
                "FADC_SIDE": row["FADC"],
                "AEB": "AEB" + row["AEB"],
                "RSR": "RSR" + row["AZnr"],
                "X": "X" + row["AEB"] + "02",
                "AZ": row["AZgr"]
                + "/"
                + row["AZnr"]
                + "AZ - "
                + row["Track1"]
                + " / "
                + row["Track2"],
                "L": f"L + {int(row['Sheet'][1:])}",
                "MNR1": 1601 + 4 * (int(row["Sheet"][1:]) - 1),
                "MNR2": 1602 + 4 * (int(row["Sheet"][1:]) - 1),
                "MNR3": 1603 + 4 * (int(row["Sheet"][1:]) - 1),
                "MNR4": 1604 + 4 * (int(row["Sheet"][1:]) - 1),
                "OP": "OP " + row["OP"][0:2] + " - " + row["OP"][-1],
                "OPNR1": int(row["OPnr"]),
                "OPNR2": int(row["OPnr"]) + 1,
                "OPNR3": int(row["OPnr"]) + 2,
                "OPNR4": int(row["OPnr"]) + 3,
                "T_CABLE": row["CableBox"],
                "T_AZ1": row["AZgr"] + "/" + row["AZnr"] + "AZ",
                "T_AZ2": row["AZgr"] + "/" + row["AZnr"] + "AZ",
                # Dictionary section mainly used for layout_block
                "BORDER_STATION": row["Station"] + " " + row["Room"],
                "BORDER_STATION_UNDERTEXT": "(" + row["Sta"] + " " + row["Room"] + ")",
                "BORDER_AZ": row["AZgr"]
                + "/"
                + row["AZnr"]
                + "AZ - "
                + row["Track1"]
                + " / "
                + row["Track2"],
                "BORDER_SHEET": row["Sheet"],
                "BORDER_CSE": row["CSE"],
                "BORDER_STATION_CODE": row["Code"],
                "BORDER_DATE": row["Date"],
                "BORDER_DOC_NAME": row["Doc"],
                "BORDER_REV": row["Rev"],
                # Dictionary section mainly used for APPCASE_BLOCK
                "CABLEAPPCASEQ": str(int(float(row["Q"]))) + "Q"
                if not pd.isna(row["Q"])
                else "nan",
                "APNR1": int(float(row["Qn"])) * 4 - 3
                if not pd.isna(row["Q"])
                else "nan",
                "APNR2": int(float(row["Qn"])) * 4 - 3 + 1
                if not pd.isna(row["Q"])
                else "nan",
                "APNR3": int(float(row["Qn"])) * 4 - 3 + 2
                if not pd.isna(row["Q"])
                else "nan",
                "APNR4": int(float(row["Qn"])) * 4 - 3 + 3
                if not pd.isna(row["Q"])
                else "nan",
                "APPCASENAME": row["CableAppCase"][-7:-2]
                if not pd.isna(row["Q"])
                else "nan",
                "CABLEAPPCASEINDEX": "Q"
                + str(int(float(row["Qn"])))
                + " OF "
                + str(int(float(row["Q"])))
                + "Q"
                if not pd.isna(row["Q"])
                else "nan",
                "CABLEAPPCASE": row["CableAppCase"] if not pd.isna(row["Q"]) else "nan",
            }
        )
    return sheetsDict


def generatesheets(
    templatefile: str,
    model_block_name: str,
    model_block_app_name: str,
    layout_block_name: str,
    dataframe,
):
    sheetsDict = updateDict(dataframe)
    template = ez.readfile(templatefile)

    for dictionary in sheetsDict:
        newdrawing = copy.deepcopy(template)
        msp = newdrawing.modelspace()
        psp = newdrawing.paperspace()
        if not dictionary["isAppcase"]:
            appcase = msp.add_auto_blockref("APPCASE_BLOCK", (0, 0), dictionary)
            appcase.explode()
        BASE_TEXT = msp.query(f'INSERT[name=="{model_block_name}"]')
        BORDER_BLOCK = psp.query(f'INSERT[name=="{layout_block_name}"]')
        for tag, value in dictionary.items():
            if BASE_TEXT[0].has_attrib(tag):
                BASE_TEXT[0].get_attrib(tag).dxf.text = value
            if BORDER_BLOCK[0].has_attrib(tag):
                BORDER_BLOCK[0].get_attrib(tag).dxf.text = value
        # Convert every block ref to seperate objects
        while insert := len(msp.query("INSERT")):
            for insert in list(msp.query("INSERT")):
                insert.explode()

        while insert := len(psp.query("INSERT")):
            for insert in list(psp.query("INSERT")):
                insert.explode()
        newdrawing.saveas(
            f"{output}{dictionary['DocDate']}-{dictionary['BORDER_DOC_NAME']}-{dictionary['Sheet']}-REV-{dictionary['BORDER_REV']}.dxf"
        )
        # odafc.export_dwg(
        #    newdrawing,
        #    f"./out/{dictionary['DocDate']}-{dictionary['BORDER_DOC_NAME']}-{dictionary['Sheet']}-REV-{dictionary['BORDER_REV']}.dxf",
        #    version="R12",
        # )


if __name__ == "__main__":
    start = time.perf_counter()
    generatesheets(
        "./templates/Ftemplate.dxf", "BASE_TEXT", "APPCASE_BLOCK", "BORDER_BLOCK", df
    )
    end = time.perf_counter()
    print(end - start)
