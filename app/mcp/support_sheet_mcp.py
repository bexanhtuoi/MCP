from fastmcp import FastMCP, Context
from dataclasses import dataclass
from contextlib import asynccontextmanager

from typing import Dict, Any, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
import google.auth
import json
import os

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/forms.body"
]

DRIVE_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")


@dataclass
class SpreadsheetContext:
    """Context for Google Spreadsheet service"""
    sheets_service: Any
    drive_service: Any
    form_service: Any
    folder_id: Optional[str] = None

@asynccontextmanager
async def spreadsheet_lifespan(server: FastMCP):
    creds = None
    if GOOGLE_SERVICE_ACCOUNT_JSON:
        try:

            creds = service_account.Credentials.from_service_account_info(
                json.loads(GOOGLE_SERVICE_ACCOUNT_JSON),
                scopes=SCOPES
            )
    
        except Exception as e:
            creds = None


    if not creds:
        try:
            print("Try ADC")
            creds, project = google.auth.default(scopes=SCOPES)
        except Exception as e:
            raise RuntimeError("All Google authentication methods failed") from e
        
    sheets_service = build('sheets', 'v4', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    form_service = build('forms', 'v1', credentials=creds)

    try:
        yield SpreadsheetContext(
            sheets_service=sheets_service,
            drive_service=drive_service,
            form_service=form_service,
            folder_id=DRIVE_FOLDER_ID
        )
    finally:
        pass


mcp = FastMCP("Support-Sheet",
              lifespan=spreadsheet_lifespan)

@mcp.tool(
    annotations={
        "title": "Get sheet file",
        "readOnlyHint": True,
    }
)
async def get_sheet_files(ctx: Context = None) -> Dict[str, dict]:
    """
    List available Google Spreadsheet files.

    Use when you need a spreadsheet_id before reading or writing data.

    Returns:
        Dict mapping spreadsheet_id to spreadsheet title and type of file.
    """
    drive_service = ctx.request_context.lifespan_context.drive_service
    folder_id = ctx.request_context.lifespan_context.folder_id

    query = "mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
    if folder_id:
        query += f" and '{folder_id}' in parents"

    result = drive_service.files().list(
        q=query,
        spaces='drive',
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        fields="files(id, name, mimeType)",
        orderBy="modifiedTime desc"
    ).execute()

    return {f["id"]: {"title": f["name"], "file_type": f["mimeType"]} for f in result.get("files", [])}



@mcp.tool(
    annotations={
        "title": "Get sheets in file",
        "readOnlyHint": True,
    }
)
async def get_sheets(spreadsheet_id: str, ctx: Context = None) -> Dict[str, str]:
    """
    List sheets (tabs) inside a spreadsheet.

    Use when you need a sheet name or sheet_id for further operations.

    Args:
        spreadsheet_id: Google Spreadsheet ID

    Returns:
        Dict mapping sheet_id to sheet title.
    """
    sheets_service = ctx.request_context.lifespan_context.sheets_service

    meta = sheets_service.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        fields="sheets(properties(sheetId,title))"
    ).execute()

    return {
        str(s["properties"]["sheetId"]): s["properties"]["title"]
        for s in meta.get("sheets", [])
    }


# Cái này tham khảo thôi nhe không nên đưa vào production vì vô nghĩa là tốn tài nguyên tính toán -> chậm app
@mcp.tool(
    annotations={
        "title": "Get number of rows in sheet",
        "readOnlyHint": True,
    }
)
async def get_row(
    spreadsheet_id: str,
    sheet: str,
    ctx: Context = None
) -> int:
    """
    Count number of non-empty rows in a sheet.

    Use to count students, records, or entries.
    """
    sheets_service = ctx.request_context.lifespan_context.sheets_service

    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=sheet
    ).execute()

    values = result.get("values", [])
    return len(values)


@mcp.tool(
    annotations={
        "title": "Get columns of sheet",
        "readOnlyHint": True,
    }
)
async def get_columns(
    spreadsheet_id: str,
    sheet: str,
    header_row: int = 1,
    ctx: Context = None
) -> list[str]:
    """
    Get column names from header row.

    Use to understand sheet structure.
    """
    sheets_service = ctx.request_context.lifespan_context.sheets_service

    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet}!{header_row}:{header_row}"
    ).execute()

    values = result.get("values", [])
    return values[0] if values else []


@mcp.tool(
    annotations={
        "title": "Read rows with filters",
        "readOnlyHint": True,
    }
)
async def read_rows_filter(
    spreadsheet_id: str,
    sheet: str,
    filters: list[dict],
    ctx: Context = None
) -> dict:
    """
    Read rows that match multiple conditions (AND logic).

    Filters format:
    [
        {"column": "<column_name>", "value": "<expected_value>"},
        ...
    ]

    Use when you need to find records by multiple conditions,
    such as student by MSSV and class, or form by email and status.
    """
    sheets_service = ctx.request_context.lifespan_context.sheets_service

    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet}!1:1000"
    ).execute()

    values = result.get("values", [])
    if not values or len(values) < 2:
        return {'success': False, "detail": f"Sheet have no data"}

    headers = values[0]
    data_rows = values[1:]

    # Lấy cột khớp đầu vào 
    filter_indexes = []
    for f in filters:
        col = f.get("column")
        if col not in headers:
            return {'success': False, "detail": f"Column '{col}' not found in sheet headers"}
        filter_indexes.append(
            (headers.index(col), str(f.get("value", "")).strip().lower())
        )

    matched_rows = []

    # Lấy dòng khớp với giá trị
    for row in data_rows:
        match = True
        for col_index, expected_value in filter_indexes:
            cell_value = row[col_index] if col_index < len(row) else ""
            if str(cell_value).strip().lower() != expected_value:
                match = False
                break

        if match:
            matched_rows.append({
                headers[i]: row[i] if i < len(row) else ""
                for i in range(len(headers))
            })
        
        if len(matched_rows) >= 20:
            break

    # Limit số records trả về để không tràn token
    return {'success': True, 'data': matched_rows}


@mcp.tool(
    annotations={
        "title": "Get form file",
        "readOnlyHint": True,
    }
)
async def get_form_files(ctx: Context = None, input: dict = {}) -> Dict[str, dict]:
    """
    List available Google Form files.

    Use when you need a form_id before reading or writing data.

    Returns:
        Dict mapping form_id to form title and type of file.
    """
    drive_service = ctx.request_context.lifespan_context.drive_service
    folder_id = ctx.request_context.lifespan_context.folder_id

    query = "mimeType='application/vnd.google-apps.form' and trashed=false"
    if folder_id:
        query += f" and '{folder_id}' in parents"

    result = drive_service.files().list(
        q=query,
        spaces='drive',
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        fields="files(id, name, mimeType)",
        orderBy="modifiedTime desc"
    ).execute()

    return {
        f["id"]: {
            "title": f["name"],
            "file_type": f["mimeType"]
        }
        for f in result.get("files", [])
    }


@mcp.tool(
    annotations={
        "title": "Get form fields",
        "readOnlyHint": True,
    }
)
async def get_form_fields(
    form_id: str,
    ctx: Context = None
) -> dict:
    """
    Get required input fields of a Google Form.

    Use this tool to know which fields must be filled before submitting a form.
    Returns sheet_id, form_url and fields information for insert data.
    """
    form_service = ctx.request_context.lifespan_context.form_service

    form = form_service.forms().get(formId=form_id).execute()

    submit_url = form.get("responderUri")
    sheet_id = form.get("linkedSheetId")
    fields = []

    for item in form.get("items", []):
        question = item.get("questionItem", {}).get("question")
        if not question:
            continue

        q_type = "unknown"
        if "textQuestion" in question:
            q_type = "text"
        elif "choiceQuestion" in question:
            q_type = question["choiceQuestion"]["type"].lower()

        fields.append({
            "title": item.get("title"),
            "type": q_type,
            "required": question.get("required", False)
        })

    return {
        "sheet_id": sheet_id,
        "form_url": submit_url,
        "fields": fields
    }



@mcp.tool(
    annotations={
        "title": "Insert Data Sheet or Sheet Form",
        "readOnlyHint": False,
        "destructiveHint": True
    }
)
async def insert_data(
    spreadsheet_id: str,
    sheet: str,
    answers: dict,
    form_url: str | None = None,
    ctx: Context = None
) -> dict:
    """
    Append data to a Google Sheet.

    Use this tool after sheet structure is known.
    If insertion fails, return the form URL so the user can submit manually.

    Args:
    answers (dict):
        Mapping of Google Sheet columns to user answers.

        Format:
            {
                "Column Name": <value> | [<value>, ...],
                ...
            }

        Notes:
        - If columns is REQUIRED FIELDS You must provide complete information; otherwise, return a request for the user to provide the missing columns.
        - Value is always sent as string
        - For checkbox questions, value can be a list of strings

    form_url (str): url form for submit form or user submit manually
    """

    sheets_service = ctx.request_context.lifespan_context.sheets_service

    try:
        header_result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet}!1:1"
        ).execute()

        headers = header_result.get("values", [[]])[0]

        if not headers:
            raise Exception("Sheet header is empty")

        row = []
        for col in headers:
            value = answers.get(col, "")
            if isinstance(value, list):
                row.append(", ".join(str(v) for v in value))
            else:
                row.append(str(value))

        sheets_service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=sheet,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]}
        ).execute()

        return {
            "success": True,
            "message": (
                "Mình đã thay bạn gửi biểu mẫu thành công rồi 🎉\n"
                "Cảm ơn bạn đã cung cấp thông tin, chúc bạn có một ngày thật tốt lành ☀️"
            )
        }

    except Exception as e:
        return {
            "success": False,
            "message": (
                "Mình chưa thể gửi biểu mẫu tự động cho bạn.\n"
                "Bạn có thể mở link dưới đây để điền và gửi thủ công nhé."
            ),
            "form_url": form_url
        }



if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8200)