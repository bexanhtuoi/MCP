from fastmcp import FastMCP

import httpx
from typing import Dict, Any, List
import os

TRELLO_BASE_URL = "https://api.trello.com/1"
API_KEY = os.environ["TRELLO_API_KEY"]
API_TOKEN = os.environ["TRELLO_API_TOKEN"]

TIMEOUT = httpx.Timeout(5.0)

mcp = FastMCP("Ticket")


def auth_params() -> dict:
    return {
        "key": API_KEY,
        "token": API_TOKEN
    }


async def trello_request(
    method: str,
    url: str,
    params: dict | None = None,
    json: dict | None = None
) -> Any:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.request(
            method,
            url,
            params={**auth_params(), **(params or {})},
            json=json
        )
        resp.raise_for_status()
        return resp.json()


@mcp.tool(
    annotations={
        "title": "Get lists of board",
        "readOnlyHint": True,
    }
)
async def get_lists() -> Dict[str, str]:
    """
    Get all lists (columns) in the Trello board.

    Use this tool when:
    - You need to know available workflow states (e.g. OPEN, PROCESSING, DONE)
    - You need a list_id before creating or moving a card

    Args:
        None (board_id is predefined in server)

    Returns:
        Dict[str, str]:
            Mapping from list_id to list_name.

        Example:
            {
                "6982b7...efc": "OPEN",
                "6982b7...efd": "PROCESSING",
                "6982b7...efe": "DONE"
            }
    """
    board_id = "6982b791ad19b87efb830ec6"
    url = f"{TRELLO_BASE_URL}/boards/{board_id}/lists"
    data = await trello_request("GET", url)

    return {lst["id"]: lst["name"] for lst in data}


@mcp.tool(
    annotations={
        "title": "Create label",
        "readOnlyHint": False,
        "destructiveHint": True
    }
)
async def create_label(
    name: str,
    color: str | None = None
) -> dict:
    """
    Create a new label in the Trello board.

    Use this tool when:
    - A suitable label does not exist yet
    - You want to classify tickets by category or priority

    Args:
        name (str):
            Label name shown on card (e.g. "Bug", "Urgent", "Question")

        color (str | None):
            Label color.
            Allowed values:
                green, yellow, orange, red, purple,
                blue, sky, lime, pink, black

            If None, Trello may assign a default color.

    Returns:
        dict:
            {
                "id": "<label_id>",
                "name": "<label_name>",
                "color": "<label_color>"
            }
    """
    try:
        url = f"{TRELLO_BASE_URL}/labels"
        data = await trello_request(
            "POST",
            url,
            params={
                "idBoard": "6982b791ad19b87efb830ec6",
                "name": name,
                "color": color
            }
        )

        return {
            "success": True,
            "data": {
                "id": data["id"],
                "name": data["name"],
                "color": data["color"]
            },
            "message": "Đã tạo label thành công 🏷️"
        }

    except Exception as e:

        return {
            "success": False,
            "message": f"Không thể tạo label: {str(e)}"
        }


@mcp.tool(
    annotations={
        "title": "Get labels of board",
        "readOnlyHint": True,
    }
)
async def get_labels() -> Dict[str, dict]:
    """
    Get all existing labels in the Trello board.

    Use this tool when:
    - You want to attach labels while creating a card
    - You need to decide whether to create a new label or reuse an existing one

    Args:
        None (board_id is predefined in server)

    Returns:
        Dict[str, dict]:
            Mapping from label_id to label information.

        Example:
            {
                "65f9...abc": {
                    "name": "Bug",
                    "color": "red"
                },
                "65f9...def": {
                    "name": "Feature",
                    "color": "green"
                }
            }
    """
    board_id = "6982b791ad19b87efb830ec6"
    url = f"{TRELLO_BASE_URL}/boards/{board_id}/labels"
    data = await trello_request("GET", url)

    return {
        lb["id"]: {
            "name": lb["name"],
            "color": lb["color"]
        }
        for lb in data
    }


@mcp.tool(
    annotations={
        "title": "Create card in Open List",
        "readOnlyHint": False,
        "destructiveHint": True
    }
)
async def create_card(
    name: str,
    desc: str | None = None,
    label_ids: List[str] | None = None
) -> dict:
    """
    Create a new card (ticket) in the OPEN list.

    Use this tool when:
    - A user submits a new issue, request, or task
    - You want to open a new ticket for tracking

    Args:
        name (str):
            Card title.
            Should be short and descriptive.

        desc (str | None):
            Card description.
            Can include details, steps, or user message.

        label_ids (List[str] | None):
            List of label IDs to attach to the card.
            - Get label IDs from `get_labels`
            - If None or empty, no labels will be attached

    Returns:
        dict:
            {
                "id": "<card_id>",
                "name": "<card_name>",
                "url": "<trello_card_url>"
            }
    """

    try:
        url = f"{TRELLO_BASE_URL}/cards"
        list_id = "6982b791ad19b87efb830efc"

        params = {
            "idList": list_id,
            "name": name,
            "desc": desc,
        }

        if label_ids:
            params["idLabels"] = ",".join(label_ids)

        data = await trello_request("POST", url, params=params)

        return {
            "success": True,
            "data": {
                "id": data["id"],
                "name": data["name"],
                "url": data["url"]
            },
            "message": "Đã tạo ticket mới thành công 🎫"
        }

    except Exception as e:

        return {
            "success": False,
            "message": (
                "Không thể tạo ticket mới. "
                "Vui lòng kiểm tra lại thông tin hoặc thử lại sau."
            )
        }


@mcp.tool(
    annotations={
        "title": "Get cards in list",
        "readOnlyHint": True,
    }
)
async def get_cards(list_id: str) -> Dict[str, dict]:
    """
    Get all cards inside a specific list.

    Use this tool when:
    - You need to see existing tickets in a workflow state
    - You want to find a card before adding a comment or updating it

    Args:
        list_id (str):
            ID of the Trello list.

    Returns:
        Dict[str, dict]:
            Mapping from card_id to card information.

        Example:
            {
                "66aa...123": {
                    "name": "Fix login bug",
                    "desc": "User cannot login after update",
                    "url": "https://trello.com/c/..."
                }
            }
    """
    url = f"{TRELLO_BASE_URL}/lists/{list_id}/cards"
    data = await trello_request("GET", url)

    return {
        c["id"]: {
            "name": c["name"],
            "desc": c["desc"],
            "url": c["url"]
        }
        for c in data
    }


@mcp.tool(
    annotations={
        "title": "Get card comments",
        "readOnlyHint": True,
    }
)
async def get_comments(card_id: str) -> list[dict]:
    """
    Retrieve all comments of a Trello card.

    Use this tool when:
    - You want to read discussion history of a ticket
    - You need context before replying or updating status

    Args:
        card_id (str):
            ID of the Trello card.

    Returns:
        List[dict]:
            List of comments ordered by time (newest first).

        Example:
            [
                {
                    "id": "67bb...xyz",
                    "text": "Please check this issue",
                    "author": "Nguyen Van A",
                    "date": "2026-02-04T08:10:00.000Z"
                }
            ]
    """
    url = f"{TRELLO_BASE_URL}/cards/{card_id}/actions"
    data = await trello_request(
        "GET",
        url,
        params={"filter": "commentCard"}
    )

    return [
        {
            "id": a["id"],
            "text": a["data"]["text"],
            "author": a["memberCreator"]["fullName"],
            "date": a["date"]
        }
        for a in data
    ]



@mcp.tool(
    annotations={
        "title": "Create comment in card",
        "readOnlyHint": False,
        "destructiveHint": True
    }
)
async def create_comment(card_id: str, text: str) -> dict:
    """
    Add a new comment to an existing Trello card.

    Use this tool when:
    - Replying to a user
    - Updating progress or asking for clarification

    Args:
        card_id (str):
            ID of the Trello card.

        text (str):
            Comment content to be added.

    Returns:
        dict:
            {
                "success": True,
                "comment_id": "<comment_id>",
                "message": "Đã thêm comment vào ticket 🎫"
            }
    """
    try:
        url = f"{TRELLO_BASE_URL}/cards/{card_id}/actions/comments"
        data = await trello_request(
            "POST",
            url,
            params={"text": text}
        )

        return {
            "success": True,
            "data": {
                "comment_id": data["id"]
            },
            "message": "Đã thêm comment vào ticket 🎫"
        }

    except Exception as e:
        return {
            "success": False,
            "message": (
                "Không thể gửi phản hồi vào ticket. "
                "Bạn có thể thử lại sau."
            )
        }



if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8400
    )
