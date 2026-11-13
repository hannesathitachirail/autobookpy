import logging
import shutil
from pathlib import Path
from tempfile import mkdtemp
from typing import Annotated

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    HTTPException,
    UploadFile,
)
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from app.generator import generate


###############################################################################
# Application paths
###############################################################################

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent

STATIC_DIR = PROJECT_DIR / "static"
TEMPLATE_DIR = PROJECT_DIR / "templates"


###############################################################################
# Logging
###############################################################################

logger = logging.getLogger(__name__)


###############################################################################
# FastAPI application
###############################################################################

app = FastAPI(
    title="Autobook CAD Generator",
    description=(
        "Upload an Autobook Excel workbook and download "
        "the generated CAD drawings as a ZIP file."
    ),
    version="0.1.0",
)


###############################################################################
# General routes
###############################################################################


@app.get("/")
def index() -> FileResponse:
    """
    Return the drag-and-drop upload page.
    """

    index_file = STATIC_DIR / "index.html"

    if not index_file.exists():
        raise HTTPException(
            status_code=500,
            detail="The application upload page could not be found.",
        )

    return FileResponse(index_file)


@app.get("/health")
def health() -> dict[str, str]:
    """
    Health endpoint used by Docker.
    """

    return {
        "status": "ok",
    }


###############################################################################
# Provide autobook.xlsx & dxfdwg.lsp
###############################################################################


@app.get("/download-template")
async def download_template():
    file_path = TEMPLATE_DIR / "autobook.xlsx"
    return FileResponse(
        path=file_path,
        filename="autobook.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.get("/download-convert")
async def download_convert():
    file_path = TEMPLATE_DIR / "dxfdwg.lsp"
    return FileResponse(
        path=file_path,
        filename="dxfdwg.lsp",
        media_type="text/plain",
    )


###############################################################################
# Autobook generation route
###############################################################################


@app.post("/generate")
async def generates(
    background_tasks: BackgroundTasks,
    workbook: Annotated[UploadFile, File()],
) -> FileResponse:
    """
    Receive an Excel workbook, generate the DXF drawings,
    ZIP the results, and return the ZIP file.
    """

    validate_upload(workbook)

    job_dir = Path(mkdtemp(prefix="autobook-"))

    input_file = job_dir / "autobook.xlsx"
    output_dir = job_dir / "out"
    zip_base = job_dir / "autobook-drawings"

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        save_uploaded_file(
            uploaded_file=workbook,
            destination=input_file,
        )

        generated_files = await run_in_threadpool(
            generate,
            input_file,
            output_dir,
            TEMPLATE_DIR,
        )

        if not generated_files:
            raise ValueError("No DXF drawings were generated.")

        zip_file = Path(
            shutil.make_archive(
                base_name=str(zip_base),
                format="zip",
                root_dir=output_dir,
            )
        )

    except ValueError as error:
        logger.exception("Autobook workbook validation failed.")

        shutil.rmtree(
            job_dir,
            ignore_errors=True,
        )

        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    except KeyError as error:
        logger.exception("The workbook is missing required data.")

        shutil.rmtree(
            job_dir,
            ignore_errors=True,
        )

        raise HTTPException(
            status_code=422,
            detail=(
                f"The workbook is missing a required sheet, column, or value: {error}"
            ),
        ) from error

    except Exception as error:
        logger.exception("Autobook generation failed.")

        shutil.rmtree(
            job_dir,
            ignore_errors=True,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "The CAD drawings could not be generated. "
                "Check the workbook data and try again."
            ),
        ) from error

    finally:
        await workbook.close()

    background_tasks.add_task(
        shutil.rmtree,
        job_dir,
        ignore_errors=True,
    )

    return FileResponse(
        path=zip_file,
        media_type="application/zip",
        filename="autobook-drawings.zip",
        background=background_tasks,
    )


###############################################################################
# Helper functions
###############################################################################


def validate_upload(
    workbook: UploadFile,
) -> None:
    """
    Perform initial validation before saving the uploaded file.
    """

    filename = Path(workbook.filename or "").name

    if not filename:
        raise HTTPException(
            status_code=400,
            detail="No workbook was selected.",
        )

    if Path(filename).suffix.lower() != ".xlsx":
        raise HTTPException(
            status_code=400,
            detail="Only .xlsx workbooks are supported.",
        )


def save_uploaded_file(
    uploaded_file: UploadFile,
    destination: Path,
) -> None:
    """
    Copy the uploaded workbook into the current job directory.
    """

    with destination.open("wb") as output_file:
        shutil.copyfileobj(
            uploaded_file.file,
            output_file,
        )
