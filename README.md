# HypeScope Bot

A Discord bot built with py-cord that monitors Hyperliquid blockchain for new token creation events.

## Features

- Monitor new token creation events on Hyperliquid
- Multi-server support with individual configurations
- Automatic message cleanup for commands
- Persistent configuration storage

## Setup

### Local Development

1. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and add your Discord bot token:

   ```
   cp .env.example .env
   ```

3. Run the bot:
   ```
   python bot.py
   ```

### Docker Deployment

1. Copy `.env.example` to `.env` and add your Discord bot token:

   ```
   cp .env.example .env
   ```

2. Build and run with Docker Compose:

   ```
   docker-compose up -d
   ```

3. View logs:

   ```
   docker-compose logs -f hypescope-bot
   ```

4. Stop the bot:
   ```
   docker-compose down
   ```

## Commands

- `/setmonitorchannel` - Set the channel for token notifications (Admin only)
- `/monitorstatus` - Get current monitoring status
- `/togglemonitor` - Enable/disable monitoring for the server (Admin only)
- `/hello` - Say hello
- `/info` - Get bot information

## Configuration

The bot automatically saves configuration in `config/token_monitor.json` including:

- Monitor channels per server
- Last checked blockchain block
- Server-specific enable/disable status
