# TruckApp MCP Server

A starter Model Context Protocol (MCP) server using Node.js and TypeScript.

## What is included

- stdio transport MCP server
- Two example tools:
  - `echo` (returns input text)
  - `get_time` (returns server timestamp)

## Prerequisites

- Node.js 18+
- npm

## Setup

```bash
npm install
```

## Development

```bash
npm run dev
```

## Build

```bash
npm run build
```

## Run built server

```bash
npm start
```

## MCP client config example

Point your MCP client to run this command from this folder:

```bash
node dist/index.js
```

For development, you can run:

```bash
npx tsx src/index.ts
```
