# Deployment Guide

## Prerequisites

- Python 3.10+
- Git
- (Optional) Docker & Docker Compose
- (Optional) Node.js 18+ (for smart contracts)

## 1. Clone & Install

```bash
git clone https://github.com/Exort-ai/Exort.git
cd Exort
pip install -e ".[all]"
```

## 2. Configure

```bash
# Copy env template
cp env.example .env

# Edit .env with your keys
# Minimum: GROQ_API_KEY (free at console.groq.com)
```

## 3. Run the CLI

```bash
Exort chat --provider groq
```

## 4. Deploy Telegram Bot

### Option A: Direct

```bash
export TELEGRAM_BOT_TOKEN=your_token_from_botfather
export GROQ_API_KEY=your_groq_key
python bot/telegram_bot.py
```

### Option B: Docker

```bash
docker compose --profile bot up -d
```

### Option C: systemd (Linux)

Create `/etc/systemd/system/Exort-bot.service`:

```ini
[Unit]
Description=Exort Telegram Bot
After=network.target

[Service]
Type=simple
User=Exort
WorkingDirectory=/opt/Exort
EnvironmentFile=/opt/Exort/.env
ExecStart=/usr/bin/python3 bot/telegram_bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable Exort-bot
sudo systemctl start Exort-bot
```

## 5. Deploy Landing Page

### GitHub Pages (Recommended)

1. Push to GitHub
2. Go to repo Settings > Pages
3. Source: GitHub Actions
4. The CI workflow auto-deploys on push to main

### Manual (nginx)

```bash
# Copy landing files
sudo cp -r landing/* /var/www/html/

# Or use Docker
docker compose --profile web up -d
# Access at http://localhost:8080
```

## 6. Deploy Smart Contract

### Testnet First

```bash
cd contracts/

# Install dependencies
npm install

# Configure .env
cp ../env.example ../.env
# Fill in: PRIVATE_KEY, BASE_SEPOLIA_RPC_URL

# Deploy to Base Sepolia testnet
npx hardhat run scripts/deploy.js --network base-sepolia

# Verify on Basescan
npx hardhat verify --network base-sepolia DEPLOYED_ADDRESS
```

### Mainnet

```bash
# After successful testnet testing:
npx hardhat run scripts/deploy.js --network base
npx hardhat verify --network base DEPLOYED_ADDRESS
```

## 7. Add Liquidity (Post-Deploy)

1. Go to https://app.uniswap.org
2. Connect wallet (deployer wallet)
3. Select Base network
4. Pool > Create new pool
5. Select MIND token + WETH or USDC
6. Set initial price and add liquidity

## 8. Verify & List

- Submit to [Basescan](https://basescan.org) for contract verification
- Submit to [CoinGecko](https://coingecko.com/en/coins/request)
- Submit to [CoinMarketCap](https://coinmarketcap.com/request/)
- Update README with contract address

## Monitoring

```bash
# Bot logs
docker compose logs -f bot

# Check bot status
curl http://localhost:8080/api/health
```
