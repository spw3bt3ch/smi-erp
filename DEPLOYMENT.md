# Render Deployment Guide

## Fixed Issues

### 1. App Import Error
- **Problem**: `gunicorn.errors.AppImportError: Failed to find attribute 'app' in 'app'`
- **Solution**: 
  - Added global `app = create_app()` variable in `app.py`
  - Created `wsgi.py` as alternative entry point
  - Updated `Procfile` to use `wsgi:app`

### 2. Database Connection Error
- **Problem**: App fails if `DATABASE_URL` is not set
- **Solution**: 
  - Added fallback to SQLite if `DATABASE_URL` is missing
  - Removed `RuntimeError` that was preventing app creation

## Files Created/Updated

### Core Files
- `app.py` - Fixed app initialization and database fallback
- `wsgi.py` - Alternative WSGI entry point
- `Procfile` - Updated to use `wsgi:app`
- `render.yaml` - Complete Render configuration

### Configuration
- `.env` - Complete environment variables
- `env.example` - Template for environment variables

## Deployment Steps

1. **Push to Git Repository**
   ```bash
   git add .
   git commit -m "Fix Render deployment issues"
   git push origin main
   ```

2. **Deploy on Render**
   - Connect your GitHub repository
   - Render will automatically detect the `Procfile`
   - Set environment variables in Render dashboard

3. **Required Environment Variables**
   ```
   DATABASE_URL=postgresql+psycopg://...
   SECRET_KEY=your-secret-key
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-app-password
   ```

## Testing Locally

```bash
# Test app import
python -c "from app import app; print('App imported successfully')"

# Test WSGI import
python -c "from wsgi import app; print('WSGI imported successfully')"

# Run with Gunicorn
gunicorn wsgi:app --bind 0.0.0.0:8000
```

## Troubleshooting

- If database connection fails, app will fallback to SQLite
- Check Render logs for detailed error messages
- Ensure all environment variables are set correctly
- Verify PostgreSQL database is accessible from Render
