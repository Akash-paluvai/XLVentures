import logging
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from backend.core.settings import settings
from backend.core.config_loader import load_domain_pack, load_accounts

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="FastAPI backend for Agentic Decision Intelligence Platform - Shift 1 V1"
)

# CORS configuration from settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def validate_domain_packs_on_startup():
    """
    On startup, load and validate all available domain packs.
    If a domain pack is invalid, the server will fail to start (Fail Early).
    """
    logger.info("Initializing and validating domain packs...")
    packs_to_validate = ["customer_success", "recruitment"]
    
    for pack_name in packs_to_validate:
        try:
            load_domain_pack(pack_name)
            logger.info(f"Successfully validated domain pack: '{pack_name}' schema matches core contract.")
        except Exception as e:
            logger.error(f"CRITICAL: Failed to validate domain pack '{pack_name}': {str(e)}")
            # Raise exception to prevent server startup
            raise RuntimeError(f"Startup check failed: Domain pack '{pack_name}' is invalid. Reason: {str(e)}")


@app.get(f"{settings.API_V1_PREFIX}/health")
def get_health():
    """
    Returns API health status.
    """
    return {"status": "healthy"}


@app.get(f"{settings.API_V1_PREFIX}/domain")
def get_domain(domain: str = Query("customer_success", description="The domain pack identifier to load")):
    """
    Loads and returns a validated domain pack configuration.
    """
    try:
        data = load_domain_pack(domain)
        return data
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid configuration or validation failure: {str(e)}")


@app.get(f"{settings.API_V1_PREFIX}/accounts")
def get_accounts(domain: str = Query("customer_success", description="The domain name to load accounts/candidates for")):
    """
    Loads and returns accounts or candidates list for the requested domain pack.
    """
    try:
        data = load_accounts(domain)
        return data
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
