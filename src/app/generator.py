from pathlib import Path

from app import dsheet
from app import esheet
from app import fsheet
from app import isheet
from app import rsheet


def generate(
    excel_file: Path,
    output_dir: Path,
    template_dir: Path,
) -> list[Path]:
    excel_file = Path(excel_file)
    output_dir = Path(output_dir)
    template_dir = Path(template_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    r_section = rsheet.RSection(str(excel_file), 2)

    r_subsections = [
        r_section.idf_signal,
        r_section.idf_points,
        r_section.op_signal,
        r_section.op_point,
        r_section.op_counter,
    ]
    for i in r_subsections:
        renderer = rsheet.DrawingRenderer(
            i.blocks, str(template_dir / "Roptemplate.dxf"), output_dir
        )
        renderer.render_sheets()

    for section in ("D", "E", "F"):
        isheet.generatesheets(
            str(template_dir / "Itemplate.dxf"), excel_file, section, output_dir
        )

    dsheet.generatesheets(
        template_dir / "Dtemplate.dxf",
        excel_file,
        r_section.op_signal.op_numbers,
        output_dir,
    )

    esheet.generatesheets(
        template_dir / "Etemplate.dxf",
        excel_file,
        r_section.op_point.op_numbers,
        output_dir,
    )

    fsheet.generatesheets(
        template_dir / "Ftemplate.dxf",
        excel_file,
        r_section.op_counter.op_numbers,
        output_dir,
    )

    generated_files = sorted(output_dir.glob("*.dxf"))
    return generated_files


if __name__ == "__main__":
    generate(Path("../autobook.xlsx"), Path("../out/"), Path("../templates/"))
