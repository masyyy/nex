# Nexus: Knowledge Graph Agent

A powerful knowledge graph system with an LLM-powered exploration agent.

## Overview

Nexus combines a custom knowledge graph library with an agentic exploration system. It allows users to build, query, and explore knowledge graphs through an intelligent agent interface that can perform automated reasoning and exploration of graph data.

## Features

- Custom knowledge graph library for creating and manipulating graph data
- Vector-based semantic search capabilities
- LLM-powered agent for intelligent graph exploration
- PDF document ingestion and knowledge extraction
- Rich command-line interface for interaction

## Requirements

- Python 3.13+
- MariaDB 11.7+ with vector extension
- OpenAI API key

## Installation

1. Clone this repository
2. Install dependencies: `pip install -e .`
3. Copy `.env.template` to `.env` and update with your configuration:
   ```
   cp .env.template .env
   # Then edit .env with your actual credentials
   ```
4. Configure your `.env` file with:
   ```
   # Option 1: Using connection URL
   DATABASE_URL=mariadb://username:password@localhost:3306/nexus

   # Option 2: Using individual parameters
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=username
   DB_PASSWORD=password
   DB_NAME=nexus

   OPENAI_API_KEY=your_openai_api_key
   ```

## Usage

### Free Prompt Mode

Interact with the agent using natural language:

```
nex "What information do we have about topic X?"
```

### Command Mode

Execute specific commands:

```
nex ingest path/to/document.pdf
```

## License

MIT
