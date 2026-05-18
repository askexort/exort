# OpenMind — Full Setup Guide

Everything you need to go from zero to launched. Follow in order.

---

## Step 1: Create GitHub Account & Repository

### Create Account
1. Go to https://github.com/signup
2. Username: `openmind-ai` (or `openmindai` if taken)
3. Email: your email
4. Password: strong password
5. Verify email

### Create Repository
1. Click "+" > "New repository"
2. Name: `openmind`
3. Description: "🧠 Free, open-source AI agent framework — AI for everyone"
4. Public
5. Do NOT initialize with README (we have one)
6. Click "Create repository"

### Push Code
```bash
cd C:/Users/D/openmind
git init
git add .
git commit -m "🧠 Initial commit: OpenMind AI framework"
git branch -M main
git remote add origin https://github.com/openmind-ai/openmind.git
git push -u origin main
```

### Enable GitHub Pages
1. Go to repo Settings > Pages
2. Source: "GitHub Actions"
3. The landing page will auto-deploy on next push

### Enable Discussions
1. Go to repo Settings > General
2. Features > Check "Discussions"
3. This becomes your community forum

---

## Step 2: Create Telegram Bot & Group

### Create Bot
1. Open Telegram, search for `@BotFather`
2. Send `/newbot`
3. Name: `OpenMind AI`
4. Username: `openmindai_bot` (must end in `bot`)
5. Copy the bot token (looks like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)
6. Send `/setdescription` to set:
   "🧠 Free AI assistant — powered by open-source models. Chat for free!"
7. Send `/setabouttext`:
   "OpenMind AI | Free & Open Source"
8. Send `/setuserpic` — upload a logo if you have one

### Create Group
1. Create new Telegram group: "OpenMind Community"
2. Add your bot to the group
3. Make bot admin (needed to read messages)
4. Set group username: `openmindai`
5. Set group description: "🧠 OpenMind AI Community — Free AI for everyone"

### Create Channel (Optional)
1. Create new channel: "OpenMind Announcements"
2. Username: `openmindann`
3. Use for project updates

### Configure Bot
```bash
# Add to .env
echo 'TELEGRAM_BOT_TOKEN=your_token_here' >> .env
echo 'GROQ_API_KEY=your_groq_key' >> .env

# Start bot
python bot/telegram_bot.py
```

---

## Step 3: Create X (Twitter) Account

### Create Account
1. Go to https://x.com/i/flow/signup
2. Name: "OpenMind AI"
3. Username: `@openmind_ai` (or `@openmindAI` if taken)
4. Use a dedicated email if possible

### Profile Setup
1. Profile picture: Logo (AI-themed, dark background)
2. Header image: "Free AI for Everyone" banner
3. Bio: "🧠 Free, open-source AI agent framework | AI for everyone | $MIND token coming soon | Built by the community 🌍"
4. Link: https://openmind-ai.github.io/openmind
5. Location: "Decentralized"

### First Tweets
Pin this tweet:
```
🧠 OpenMind is live!

Free AI for everyone. Open source. No paywalls.

✅ AI Agent Framework
✅ Free Chat (Telegram bot)
✅ $MIND Token (coming soon)
✅ 100% Open Source (MIT)

Star us: github.com/openmind-ai/openmind

#AI #OpenSource #Crypto #BaseChain #DeFi
```

Daily content ideas:
- AI tips and tutorials
- Project updates
- Crypto/AI intersection news
- Community highlights
- Meme-worthy AI content

---

## Step 4: Create Discord Server (Optional but Recommended)

1. Open Discord, click "+" to create server
2. Name: "OpenMind AI"
3. Channels:
   - #announcements
   - #general
   - #dev-chat
   - #bot-support
   - #token-talk
   - #showcase
4. Set up roles: Admin, Moderator, Developer, Community
5. Create invite link (never expires)
6. Add to README and landing page

---

## Step 5: Get Free API Keys

### Groq (Free — No Credit Card)
1. Go to https://console.groq.com
2. Sign up with email
3. Go to API Keys > Create
4. Copy key (starts with `gsk_`)
5. Free tier: 14,400 requests/day, very fast

### Ollama (Free — Local)
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama3.1:8b

# It runs on http://localhost:11434
```

---

## Step 6: Deploy Smart Contract to Testnet

### Prerequisites
```bash
cd C:/Users/D/openmind/contracts
npm install
```

### Get Testnet ETH
1. Go to https://www.alchemy.com/faucets/base-sepolia
2. Connect wallet
3. Get free Base Sepolia ETH

### Configure
```bash
cp ../env.example ../.env
# Edit .env:
# PRIVATE_KEY=your_wallet_private_key
# BASE_SEPOLIA_RPC_URL=https://sepolia.base.org
# BASESCAN_API_KEY=get from basescan.org
```

### Deploy
```bash
npx hardhat run scripts/deploy.js --network base-sepolia
```

### Verify
```bash
npx hardhat verify --network base-sepolia CONTRACT_ADDRESS
```

### Test
- Verify on https://sepolia.basescan.org
- Test token functions (transfer, approve, etc.)

---

## Step 7: Launch Token on Mainnet

### Prerequisites
- Base mainnet ETH for gas (~$2-5)
- Tested contract on testnet
- Audit (optional but recommended for credibility)

### Deploy
```bash
npx hardhat run scripts/deploy.js --network base
npx hardhat verify --network base CONTRACT_ADDRESS
```

### Add Liquidity
1. Go to https://app.uniswap.org
2. Connect deployer wallet
3. Switch to Base network
4. Pool > New Position
5. Select MIND / USDC or MIND / WETH
6. Set initial price (e.g., $0.0001 per MIND)
7. Add liquidity (minimum $50-100 worth)

### Lock Liquidity
- Use https://team.finance or https://unicrypt.network
- Lock LP tokens for 6-12 months (builds trust)

---

## Step 8: List on Aggregators

### CoinGecko
1. Go to https://coingecko.com/en/coins/request
2. Fill form with contract address, website, socials
3. Wait 3-7 days

### CoinMarketCap
1. Go to https://coinmarketcap.com/request/
2. Fill form
3. Wait 7-14 days

### DEX Screener
1. Go to https://dexscreener.com
2. Search your token — it auto-indexes
3. Update profile with logo, description, links

### BaseScan Token Tracker
- Auto-indexed after verification

---

## Step 9: Marketing & Community Growth

### Week 1: Launch
- [ ] Push all code to GitHub
- [ ] Start Telegram bot
- [ ] First tweets
- [ ] Post in r/cryptocurrency, r/ethereum, r/defi
- [ ] Post in crypto Discord servers
- [ ] Submit to Product Hunt

### Week 2: Growth
- [ ] Daily tweets
- [ ] Telegram group engagement
- [ ] Airdrop announcement (tasks: follow, join, star repo)
- [ ] Reach out to crypto influencers
- [ ] Blog post: "Why we built OpenMind"

### Week 3-4: Expand
- [ ] First airdrop distribution
- [ ] Partnership announcements
- [ ] Tutorial videos
- [ ] Developer bounties
- [ ] CEX listing applications

### Content Calendar
| Day | Platform | Content |
|-----|----------|---------|
| Mon | X | Technical thread |
| Tue | Telegram | Community poll |
| Wed | X | Tutorial/tip |
| Thu | Discord | Dev update |
| Fri | X | Meme/casual |
| Sat | Blog | Weekly recap |
| Sun | Rest | — |

---

## Quick Reference

| Thing | URL |
|-------|-----|
| GitHub | github.com/openmind-ai/openmind |
| Website | openmind-ai.github.io/openmind |
| Telegram | t.me/openmindai |
| X | x.com/openmind_ai |
| Groq Console | console.groq.com |
| Base Chain | base.org |
| Uniswap | app.uniswap.org |
| CoinGecko | coingecko.com |

---

## Environment Variables Summary

```bash
# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC...

# AI Providers
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=sk-...

# Blockchain
PRIVATE_KEY=0x...
BASE_RPC_URL=https://mainnet.base.org
BASE_SEPOLIA_RPC_URL=https://sepolia.base.org
BASESCAN_API_KEY=...

# Bot Config
DEFAULT_MODEL=llama-3.3-70b-versatile
RATE_LIMIT_PER_MIN=5
ADMIN_IDS=your_telegram_id
```

---

**You're ready. Go build the future of free AI. 🧠🚀**
