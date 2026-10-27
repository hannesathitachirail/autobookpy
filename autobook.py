import dsheet, esheet, fsheet, isheet
import time


excelsheet = "./autobook.xlsx"
output = "./out/"

if __name__ == "__main__":
    start = time.perf_counter()
    isheet.generatesheets("./templates/Itemplate.dxf", excelsheet, "D")
    isheet.generatesheets("./templates/Itemplate.dxf", excelsheet, "E")
    isheet.generatesheets("./templates/Itemplate.dxf", excelsheet, "F")
    dsheet.generatesheets("./templates/Dtemplate.dxf", excelsheet)
    esheet.generatesheets("./templates/Etemplate.dxf", excelsheet)
    fsheet.generatesheets("./templates/Ftemplate.dxf", excelsheet)
    end = time.perf_counter()
    print(f"Elapse time: {end - start:.0f}")
