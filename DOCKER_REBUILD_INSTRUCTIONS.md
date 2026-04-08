# 🐳 Docker Rebuild Instructions

## Changes Made to Dockerfile

✅ Added nodejs and npm installation:
```dockerfile
RUN apt-get update && apt-get install -y nodejs npm curl && rm -rf /var/lib/apt/lists/*
```

This enables:
- npm verification steps
- Frontend preview compilation
- Frontend dependency checking

## Build Command

```bash
# Build Docker image with all fixes
docker build -t crucibai:production-fixed .

# Or if using Railway CLI:
railway build --environment production
```

## Expected Build Steps

1. ✅ Python 3.11 base image
2. ✅ System dependencies (build-essential, etc.)
3. ✅ nodejs + npm installation (NEW)
4. ✅ Python dependencies
5. ✅ Application setup

## Verification

After build:
```bash
# Check npm is available
docker run crucibai:production-fixed npm --version

# Should output: v<version>
```

## Railway Deployment

Railway will automatically:
1. Detect Dockerfile changes
2. Rebuild image
3. Deploy new version
4. Run migrations

No additional steps needed if using Railway CLI.

## Time Estimate

- Local build: 15 minutes
- Railway build: 10 minutes (parallel with deployment)
- Total: 15 minutes

