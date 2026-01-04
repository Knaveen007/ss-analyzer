# src/api/monitoring.py
from prometheus_client import Counter, Histogram, generate_latest

# Metrics
UPLOADS_TOTAL = Counter('memory_uploads_total', 'Total uploads')
PROCESSING_TIME = Histogram('memory_processing_seconds', 'Processing time')
CACHE_HITS = Counter('memory_cache_hits', 'Cache hits')
API_ERRORS = Counter('memory_api_errors', 'API errors')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "database": db.check_connection(),
        "cache": cache.check_health(),
        "api_keys": check_api_keys()
    }