# 🚢 Ghost Developer Deployment Guide

This guide details how to move your **Ghost Developer** from local testing to a 24/7 production-grade autonomous agent platform.

---

## 🛠️ GitHub Webhook Setup

The "Ghost" listens for events from your GitHub repositories. 

1. **Repo Settings**: Go to `Settings` -> `Webhooks` -> `Add webhook`.
2. **Payload URL**: `https://<your-server-url>/webhook`.
3. **Content Type**: Must be `application/json`.
4. **Events**: Select **"Let me select individual events"** and check:
   - [x] **Issues**
   - [x] **Issue comments**
5. **Secret**: (Optional) For high security, add a webhook secret.

> [!IMPORTANT]
> Ghost Developer only responds to tasks where **`@DevAgent`** is mentioned in the issue or comment.

---

## ☁️ One-Click Deployment Options

Ghost Developer is pre-configured for modern cloud platforms that support Docker.

| Platform | Link | Strategy |
| :--- | :--- | :--- |
| **Railway** | [![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new) | Connect GitHub -> **Deploy**. |
| **Render** | [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy) | New **Web Service** -> Use Docker. |
| **DigitalOcean** | [App Platform](https://www.digitalocean.com/products/app-platform) | Automated Docker build. |

---

## 🔑 Environment Variables

You must define these variables in your production dashboard (Render/Railway/etc.):

| Variable | Required | Description |
| :--- | :--- | :--- |
| `ANTHROPIC_API_KEY` | Yes | Your Claude API Key. |
| `GITHUB_TOKEN` | Yes | Token with `repo` scope to clone and open PRs. |
| `CLAUDE_MODEL` | No | Default: `haiku`. Set to `sonnet` for heavy lifting. |
| `PORT` | No | Default: `8765`. Cloud providers often override this. |

---

## 🐳 Manual Docker Deployment

If you are using a VPS (DigitalOcean Droplet, AWS EC2):

```bash
# Build the image
docker build -t ghost-dev .

# Run the container
docker run -d \
  -p 8765:8765 \
  --env ANTHROPIC_API_KEY=your_key \
  --env GITHUB_TOKEN=your_token \
  --name ghost-dev-instance \
  ghost-dev
```

---

## 🛡️ Security Hardening

- **Fine-Grained PAT**: On GitHub, create a "Fine-grained personal access token" that only has access to the repositories you want the Ghost to manage.
- **SSL/TLS**: Ensure your cloud URL uses `https://` (Railway/Render handle this automatically).
- **IP White-listing**: For extreme security, only allow traffic to `/webhook` from [GitHub's official IP ranges](https://api.github.com/meta).
