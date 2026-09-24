# MarketMCP-Agent

An MCP-powered financial reference data agent that answers questions about available market data using the Kaiko Reference Data API.

## Overview

MarketMCP-Agent implements a Model Context Protocol (MCP) interface for the Kaiko Reference Data API and connects it to a simple AI agent. The agent can query available exchanges, instruments, and derivatives data through MCP tools, then generate natural-language answers for market data availability questions.

The project demonstrates how MCP can be used to expose financial data APIs as tools for autonomous analyst and data engineering agents.

## What This Project Does

The system includes two main components:

1. `kaiko_mcp_server.py`
   - Implements a FastMCP server
   - Wraps Kaiko Reference Data API endpoints
   - Exposes tools for retrieving exchanges and instruments
   - Allows an agent to query market data availability through MCP

2. `market_data_agent.py`
   - Starts or connects to the MCP server
   - Accepts a natural-language user question
   - Calls the appropriate MCP tools
   - Generates a final answer using retrieved Kaiko reference data

## Example Questions

The agent is designed to answer questions such as:

```text
What major derivatives exchanges are available?
```

```text
When was Synapse last traded on Coinbase?
```

```text
What instruments are available for a given exchange?
```

## Features

- Model Context Protocol implementation
- FastMCP server integration
- Kaiko Reference Data API wrapper
- Agentic tool-use workflow
- Exchange lookup
- Instrument lookup
- Natural-language question answering
- Financial data availability analysis
- OpenAI-powered response generation
- Environment-based API key management

## Tech Stack

- Python
- FastMCP
- Model Context Protocol
- Kaiko Reference Data API
- OpenAI API
- Requests
- python-dotenv

## Project Structure

```text
MarketMCP-Agent/
│
├── market_data_agent.py
├── kaiko_mcp_server.py
├── requirements.txt
├── pipeline_execution.png
├── README.md
└── .gitignore
```

## Installation

Clone the repository:

```bash
git clone https://github.com/78himanshu/MarketMCP-Agent.git
cd MarketMCP-Agent
```

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Environment Setup

Create a `.env` file in the project root:

```text
OPENAI_API_KEY=your_openai_api_key_here
KAIKO_API_KEY=your_kaiko_api_key_here
```

The `.env` file is excluded from version control.

## Usage

Run the agent with a question:

```bash
python market_data_agent.py "What major derivatives exchanges are available?"
```

Example output:

```text
Starting MCP server 'Kaiko Reference Data MCP' with transport 'stdio'

Answer:
There is one major derivatives exchange available according to Kaiko data: BTMX.
```

## MCP Workflow

```text
User Question
     │
     ▼
Market Data Agent
     │
     ▼
FastMCP Server
     │
     ├── Exchanges Tool
     └── Instruments Tool
     │
     ▼
Kaiko Reference Data API
     │
     ▼
Retrieved Market Metadata
     │
     ▼
Natural-Language Answer
```

## Why This Matters

Modern AI agents need safe, structured ways to access external systems. MCP provides a standardized interface for exposing APIs, tools, and data sources to AI agents.

MarketMCP-Agent demonstrates how a financial data API can be turned into an agent-usable tool layer, which is useful for:

- Trading data discovery
- Market data availability checks
- Autonomous analyst workflows
- Data engineering assistants
- API tool orchestration
- Financial AI agents

## Future Improvements

- Add support for additional Kaiko endpoints
- Add filtering by exchange, asset, instrument class, and date range
- Add structured JSON output
- Add better source-level tracing for tool calls
- Add caching for repeated API queries
- Add richer error handling for unavailable instruments
- Add a CLI interface with optional flags

## Author

Himanshu Hemant Paithane

