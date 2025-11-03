# 🔐 Setup Guide: Get Credentials & Deploy to Azure

## Prerequisites

- Azure CLI installed: `az --version`
- Access to your Azure subscription
- Admin access to your GitHub repository

---

## Step 1: Login to Azure

```bash
# Login to Azure (opens browser)
az login

# Verify you're logged in
az account show
```

---

## Step 2: Register Azure Container Registry Provider

**Required for Azure for Students subscriptions** - register the Container Registry service:

```bash
# Register the Container Registry provider (takes ~1 minute)
az provider register --namespace Microsoft.ContainerRegistry

# Wait for registration to complete
az provider show --namespace Microsoft.ContainerRegistry --query "registrationState"
```

Wait until you see `"Registered"` in the output before continuing.

---

## Step 3: Create Azure Container Registry

This registry will store your Docker images.

```bash
# Create the container registry in your 'college' resource group
az acr create \
  --resource-group college \
  --name cracalbummaker \
  --sku Basic \
  --admin-enabled true
```

**Note:** If the `college` resource group doesn't exist, create it first:
```bash
az group create --name college --location eastus
```

---

## Step 4: Get the 3 Required Credentials

### 🔑 Credential 1: AZURE_CREDENTIALS

This is a Service Principal that allows GitHub Actions to deploy to Azure.

```bash
# Get your subscription ID
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

# Create a service principal with contributor access to 'college' resource group
az ad sp create-for-rbac \
  --name "github-album-maker-deploy" \
  --role contributor \
  --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/college \
  --json-auth
```

**Copy the entire JSON output** - it looks like this:

```json
{
  "clientId": "12345678-1234-1234-1234-123456789012",
  "clientSecret": "abcdefghijklmnopqrstuvwxyz",
  "subscriptionId": "87654321-4321-4321-4321-210987654321",
  "tenantId": "11111111-1111-1111-1111-111111111111"
}
```

✅ **Save this entire JSON** - you'll paste it as `AZURE_CREDENTIALS` in GitHub

---

### 🔑 Credential 2 & 3: ACR_USERNAME and ACR_PASSWORD

Get your Azure Container Registry credentials:

```bash
az acr credential show --name cracalbummaker --resource-group college
```

Output looks like:
```json
{
  "passwords": [
    {
      "name": "password",
      "value": "YOUR_ACR_PASSWORD_HERE"
    },
    {
      "name": "password2",
      "value": "ANOTHER_PASSWORD"
    }
  ],
  "username": "cracalbummaker"
}
```

✅ **ACR_USERNAME** = `cracalbummaker` (the username from output)  
✅ **ACR_PASSWORD** = Copy the first password value

---

## Step 5: Add Secrets to GitHub

### Option A: Using GitHub Website (Easiest)

1. Go to your repository: `https://github.com/yp-ac/album-maker`
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret:

| Name | Value |
|------|-------|
| `AZURE_CREDENTIALS` | The entire JSON from Step 3, Credential 1 |
| `ACR_USERNAME` | `cracalbummaker` |
| `ACR_PASSWORD` | The password value from Step 3, Credential 2 & 3 |

### Option B: Using GitHub CLI (Faster)

```bash
# Install GitHub CLI if needed
# macOS: brew install gh
# Linux: sudo apt install gh

# Login to GitHub
gh auth login

# Set the secrets (you'll be prompted to paste each value)
gh secret set AZURE_CREDENTIALS
# Paste the entire JSON from Step 3, Credential 1, then press Ctrl+D

gh secret set ACR_USERNAME -b "cracalbummaker"

gh secret set ACR_PASSWORD
# Paste the password from Step 3, then press Ctrl+D
```

---

## Step 6: Deploy Infrastructure

Before GitHub Actions can deploy your app, the Azure infrastructure must exist.

```bash
# Navigate to your project
cd /home/yashp/learning/01-College/5SEM/DAA/album-maker

# Deploy using Azure CLI
az deployment group create \
  --resource-group college \
  --template-file infrastructure/main.bicep \
  --parameters infrastructure/parameters.json
```

This creates:
- ✅ Azure Container Registry (`cracalbummaker`)
- ✅ App Service Plan (`asp-album-maker`)
- ✅ Web App (`app-album-maker`)
- ✅ Application Insights (`appi-album-maker`)
- ✅ Storage Account (`stalbummaker`)

**This takes ~5 minutes** ⏱️

---

## Step 7: Trigger Deployment

### Automatic Deployment
Push any commit to the `main` branch:
```bash
git add .
git commit -m "Deploy to Azure"
git push origin main
```

### Manual Deployment
1. Go to your repository on GitHub
2. Click **Actions** → **CD Pipeline - Deploy to Azure**
3. Click **Run workflow** → **Run workflow**

---

## Step 8: Access Your App

After deployment completes (~5-10 minutes):

🌐 **Your app:** `https://app-album-maker.azurewebsites.net`

---

## Verification Checklist

- [ ] Logged into Azure (`az account show`)
- [ ] Created ACR in 'college' resource group
- [ ] Got `AZURE_CREDENTIALS` JSON
- [ ] Got `ACR_USERNAME` and `ACR_PASSWORD`
- [ ] Added all 3 secrets to GitHub
- [ ] Deployed infrastructure with `az deployment group create`
- [ ] Triggered GitHub Actions workflow
- [ ] App is accessible at the URL

---

## Troubleshooting

### "The subscription is not registered to use namespace 'Microsoft.ContainerRegistry'"
```bash
# Register the provider
az provider register --namespace Microsoft.ContainerRegistry

# Check registration status
az provider show --namespace Microsoft.ContainerRegistry --query "registrationState"

# Wait until it shows "Registered" (takes ~1 minute)
```

### "Resource group 'college' not found"
```bash
az group create --name college --location eastus
```

### "Service principal already exists"
```bash
# Delete the old one first
az ad sp delete --id $(az ad sp list --display-name "github-album-maker-deploy" --query "[0].appId" -o tsv)
# Then re-run the create-for-rbac command
```

### "GitHub Actions failing"
1. Check secrets are set correctly in GitHub Settings → Secrets
2. Look at the error logs in Actions tab
3. Verify infrastructure is deployed: `az resource list -g college -o table`

### "ACR credentials not working"
```bash
# Regenerate ACR password
az acr credential renew --name cracalbummaker --password-name password
# Get the new credentials
az acr credential show --name cracalbummaker
# Update ACR_PASSWORD secret in GitHub
```

---

## Quick Reference Commands

```bash
# Check what resources exist in 'college'
az resource list -g college -o table

# Check ACR exists
az acr show --name cracalbummaker --resource-group college

# Check Web App exists
az webapp show --name app-album-maker --resource-group college

# View GitHub secrets (names only, not values)
gh secret list

# Test your app locally with Docker
docker-compose up
```

---

**Need help?** Check the GitHub Actions logs in the **Actions** tab of your repository.
