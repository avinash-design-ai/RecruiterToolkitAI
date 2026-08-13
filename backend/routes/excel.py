from fastapi import APIRouter, UploadFile, File
from fastapi.responses import FileResponse
import tempfile
import shutil
import os

from modules.wagecalculator_web.main import main

router = APIRouter()

# Stores generated files temporarily
GENERATED_FILES = {}


# ------------------------------------------------------
# Process Excel
# ------------------------------------------------------

@router.post("/wage/excel")
def process_excel(file: UploadFile = File(...)):

    temp_dir = tempfile.mkdtemp()

    input_file = os.path.join(
        temp_dir,
        file.filename
    )

    with open(input_file, "wb") as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )

    filename = "Prevailing_Wage_Updated.xlsx"

    output_file = os.path.join(
        temp_dir,
        filename
    )

    main(

        file_path=input_file,

        output_path=output_file

    )

    GENERATED_FILES[filename] = output_file

    return {

        "success": True,

        "filename": filename

    }


# ------------------------------------------------------
# Download Excel
# ------------------------------------------------------

@router.get("/wage/download/{filename}")
def download_excel(filename: str):

    if filename not in GENERATED_FILES:

        return {

            "success": False,

            "message": "File not found."

        }

    return FileResponse(

        GENERATED_FILES[filename],

        filename=filename,

        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    )
