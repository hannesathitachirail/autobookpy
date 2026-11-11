import dsheet, esheet, fsheet, isheet, rsheet
import time


excelsheet = "./autobook.xlsx"
output = "./out/"

if __name__ == "__main__":
    start = time.perf_counter()
    r_section = rsheet.RSection("./autobook.xlsx", 2)
    rsheet.DrawingRenderer(
        r_section.idf_signal.blocks, "./templates/Roptemplate.dxf"
    ).render_sheets()
    rsheet.DrawingRenderer(
        r_section.idf_points.blocks, "./templates/Roptemplate.dxf"
    ).render_sheets()
    rsheet.DrawingRenderer(
        r_section.op_signal.blocks, "./templates/Roptemplate.dxf"
    ).render_sheets()
    rsheet.DrawingRenderer(
        r_section.op_point.blocks, "./templates/Roptemplate.dxf"
    ).render_sheets()
    rsheet.DrawingRenderer(
        r_section.op_counter.blocks, "./templates/Roptemplate.dxf"
    ).render_sheets()
    isheet.generatesheets("./templates/Itemplate.dxf", excelsheet, "D")
    isheet.generatesheets("./templates/Itemplate.dxf", excelsheet, "E")
    isheet.generatesheets("./templates/Itemplate.dxf", excelsheet, "F")
    dsheet.generatesheets(
        "./templates/Dtemplate.dxf", excelsheet, r_section.op_signal.op_numbers
    )
    esheet.generatesheets("./templates/Etemplate.dxf", excelsheet)
    fsheet.generatesheets("./templates/Ftemplate.dxf", excelsheet)
    end = time.perf_counter()
    print(f"Elapse time: {end - start:.0f}")
    start = time.perf_counter()

    end = time.perf_counter()
    print(f"Batch time: {end - start:.0f}")
