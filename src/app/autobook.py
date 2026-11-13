import dsheet, esheet, fsheet, isheet, rsheet
import time


if __name__ == "__main__":
    start = time.perf_counter()
    r_section = rsheet.RSection(excelsheet, 2)
    rsheet.DrawingRenderer(
        r_section.idf_signal.blocks, "../templates/Roptemplate.dxf"
    ).render_sheets()
    rsheet.DrawingRenderer(
        r_section.idf_points.blocks, "../templates/Roptemplate.dxf"
    ).render_sheets()
    rsheet.DrawingRenderer(
        r_section.op_signal.blocks, "../templates/Roptemplate.dxf"
    ).render_sheets()
    rsheet.DrawingRenderer(
        r_section.op_point.blocks, "../templates/Roptemplate.dxf"
    ).render_sheets()
    rsheet.DrawingRenderer(
        r_section.op_counter.blocks, "../templates/Roptemplate.dxf"
    ).render_sheets()
    isheet.generatesheets("../templates/Itemplate.dxf", excelsheet, "D")
    isheet.generatesheets("../templates/Itemplate.dxf", excelsheet, "E")
    isheet.generatesheets("../templates/Itemplate.dxf", excelsheet, "F")
    dsheet.generatesheets(
        "../templates/Dtemplate.dxf", excelsheet, r_section.op_signal.op_numbers
    )
    esheet.generatesheets(
        "../templates/Etemplate.dxf", excelsheet, r_section.op_point.op_numbers
    )
    fsheet.generatesheets(
        "../templates/Ftemplate.dxf", excelsheet, r_section.op_counter.op_numbers
    )
    end = time.perf_counter()
    print(f"Elapse time: {end - start:.0f}")
