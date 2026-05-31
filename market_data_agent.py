from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

from dotenv import load_dotenv
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing from .env")

client = OpenAI(api_key=OPENAI_API_KEY)


def build_openai_tools(mcp_tools: list[Any]) -> list[dict[str, Any]]:
    """
    Convert MCP tool schemas into OpenAI function tool schemas.
    """
    converted = []

    for tool in mcp_tools:
        schema = tool.inputSchema or {"type": "object", "properties": {}}

        converted.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": schema,
                },
            }
        )

    return converted


def extract_text_from_mcp_result(result: Any) -> str:
    """
    Safely convert an MCP tool result into a string for the model.
    """
    if getattr(result, "data", None) is not None:
        try:
            return json.dumps(result.data, ensure_ascii=False)
        except TypeError:
            return str(result.data)

    chunks = []
    for item in getattr(result, "content", []):
        text = getattr(item, "text", None)
        if text:
            chunks.append(text)

    return "\n".join(chunks) if chunks else "No tool output returned."


async def answer_question(question: str) -> str:
    """
    Connect to the local MCP server over stdio, expose the MCP tools to the model,
    and run a simple tool-calling loop.
    """
    transport = StdioTransport(
        command=sys.executable,
        args=["hpaithan_mcp_server.py"],
        env={
            "KAIKO_API_KEY": os.getenv("KAIKO_API_KEY", ""),
        },
        cwd=os.getcwd(),
    )

    mcp_client = Client(transport)

    async with mcp_client:
        tools = await mcp_client.list_tools()
        openai_tools = build_openai_tools(tools)

        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are a helpful agent answering questions about data available "
                    "through the Kaiko Reference Data API. "
                    "Use the provided tools whenever the answer depends on available "
                    "exchanges, instruments, derivatives availability, or trade windows. "
                    "If the user asks when something was last traded, inspect the tool "
                    "result carefully: if trade_end_time is null, say the instrument is "
                    "still active and Kaiko does not show an ended last-trade date."
                ),
            },
            {
                "role": "user",
                "content": question,
            },
        ]

        max_rounds = 8

        for _ in range(max_rounds):
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                temperature=0,
                messages=messages,
                tools=openai_tools,
                tool_choice="auto",
            )

            message = response.choices[0].message

            if message.tool_calls:
                assistant_message = {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [],
                }

                for tool_call in message.tool_calls:
                    assistant_message["tool_calls"].append(
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments,
                            },
                        }
                    )

                messages.append(assistant_message)

                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        tool_args = json.loads(tool_call.function.arguments or "{}")
                    except json.JSONDecodeError:
                        tool_args = {}

                    try:
                        tool_result = await mcp_client.call_tool(tool_name, tool_args)
                        tool_output = extract_text_from_mcp_result(tool_result)
                    except Exception as exc:
                        tool_output = json.dumps(
                            {"error": f"Tool call failed: {str(exc)}"},
                            ensure_ascii=False,
                        )

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_output,
                        }
                    )
            else:
                return message.content or "No answer was generated."

        return "Stopped after too many tool-calling rounds."


def main() -> None:
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:]).strip()
    else:
        question = input("Ask a Kaiko reference-data question: ").strip()

    if not question:
        raise ValueError("Please provide a question.")

    answer = asyncio.run(answer_question(question))
    print("\nAnswer:\n")
    print(answer)


if __name__ == "__main__":
    main()