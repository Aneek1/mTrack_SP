# LLM Integration Setup Guide

This document explains how to set up and use the actual LLM models for the visual inspection AI.

## Overview

The mTrac SP simulation now supports real AI models from OpenAI and Anthropic for more intelligent inspection behavior. The AI will:

- Systematically scan the PCBA board
- Make strategic inspection decisions
- Provide detailed logging of inspection activities
- Identify and prioritize defect detection

## Supported Providers

### OpenAI
- **Models**: GPT-4o-mini (recommended for cost/quality balance)
- **API**: OpenAI Chat Completions API
- **Cost**: ~$0.15 per 1M input tokens, $0.60 per 1M output tokens

### Anthropic
- **Models**: Claude-3-haiku (recommended for cost/quality balance)
- **API**: Anthropic Messages API
- **Cost**: ~$0.25 per 1M input tokens, $1.25 per 1M output tokens

### Google Gemini
- **Models**: Gemini-1.5-flash (recommended for cost/quality balance)
- **API**: Google Generative AI API
- **Cost**: ~$0.075 per 1M input tokens, $0.30 per 1M output tokens

## Setup Instructions

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure API Keys

Copy the example environment file:

```bash
cp backend/.env.example backend/.env
```

Edit the `.env` file with your API keys:

```bash
# For OpenAI
OPENAI_API_KEY=sk-your-openai-key-here
LLM_PROVIDER=openai

# OR for Anthropic
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
LLM_PROVIDER=anthropic

# OR for Google Gemini
GEMINI_API_KEY=your-gemini-key-here
LLM_PROVIDER=gemini
```

### 3. Get API Keys

#### OpenAI
1. Visit https://platform.openai.com/api-keys
2. Create a new API key
3. Copy the key to your `.env` file

#### Anthropic
1. Visit https://console.anthropic.com/
2. Create an account and add payment method
3. Generate an API key
4. Copy the key to your `.env` file

#### Google Gemini
1. Visit https://makersuite.google.com/app/apikey
2. Create a new API key
3. Copy the key to your `.env` file

### 4. Run the Backend

```bash
cd backend
python server.py
```

The backend will automatically use the configured LLM provider. If API keys are not set, it will fall back to the placeholder logic.

## Usage

### Start the UI

```bash
cd ui
npm run dev
```

### AI Behavior

With real LLM integration, the inspection AI will:

1. **Intelligent Scanning**: Use systematic patterns (raster, spiral, grid) to cover the board efficiently
2. **Defect Focus**: Prioritize areas likely to contain defects
3. **Detailed Logging**: Provide rich descriptions of inspection activities
4. **Safety Compliance**: Always stay within board boundaries and move efficiently

### Monitoring

The UI now shows enhanced defect information:
- **Real-time Statistics**: Pass/fail rates, total inspected components
- **Visual Alerts**: Defective components highlighted with warning badges
- **Detailed Logs**: AI thought process and decision rationale

## Cost Management

### Estimated Usage
- Typical inspection session: ~50-100 API calls
- Average tokens per call: ~200-400
- Estimated cost per session:
  - OpenAI: $0.01-0.05
  - Anthropic: $0.02-0.08
  - Gemini: $0.005-0.03 (most cost-effective)

### Cost Optimization Tips
1. Use Gemini-1.5-flash for best cost-effectiveness
2. Use GPT-4o-mini or Claude-3-haiku for balanced cost/quality
3. Monitor usage in your provider's dashboard
4. Set spending limits in your API provider account

## Troubleshooting

### API Key Issues
- Verify the key is correctly copied (no extra spaces)
- Check the key has sufficient credits/balance
- Ensure the key is for the correct provider

### Connection Issues
- Check internet connectivity
- Verify API provider status pages
- Ensure firewall allows API connections

### Fallback Mode
If API calls fail, the system automatically falls back to placeholder logic and continues operation.

## Advanced Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openai` | Choose between `openai`, `anthropic`, or `gemini` |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | - | Anthropic API key |
| `GEMINI_API_KEY` | - | Google Gemini API key |

### Model Selection

The system uses optimized models by default:
- OpenAI: `gpt-4o-mini`
- Anthropic: `claude-3-haiku`
- Gemini: `gemini-1.5-flash`

These provide the best balance of cost, speed, and quality for inspection tasks.

## Security Notes

- Keep API keys secure and never commit them to version control
- Use environment variables, not hardcoded keys
- Regularly rotate API keys for security
- Monitor API usage for unusual activity
