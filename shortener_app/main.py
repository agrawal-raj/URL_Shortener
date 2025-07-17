import secrets
from fastapi import Depends, FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import validators
from . import crud, models, schemas
from .database import SessionLocal, engine
from .config import get_settings
from starlette.datastructures import URL
from fastapi.middleware import Middleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.sessions import SessionMiddleware



middleware=[
    Middleware(SessionMiddleware, secret_key=secrets.token_hex(32))
]
app = FastAPI(middleware=middleware)
app.mount("/static", StaticFiles(directory="static"), name= "static")
templates = Jinja2Templates(directory="templates")

models.Base.metadata.create_all(bind=engine)

#dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def raise_bad_request(message):
    raise HTTPException(status_code=400, detail=message)

def raise_not_found(request):
    message = f"URL '{request.url}' doesn't exist"
    raise HTTPException(status_code=404, detail=message)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/", response_class= HTMLResponse)
async def create_url(request: Request, target_url: str = Form(...), db:Session = Depends(get_db)):
    # Generate CSRF token
    request.session.setdefault("csrf_token", secrets.token_hex(16))

    if not validators.url(target_url):
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": "Please enter a valid URL"
        }, status_code=400)
    
    try:
        db_url = crud.create_db_url(db=db, url=schemas.URLBase(target_url=target_url))
        base_url = get_settings().base_url
        return RedirectResponse(f"/success/{db_url.secret_key}", status_code=303)
    except Exception as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": f"Error creating short URL: {str(e)}" 
        }, status_code=500)
        

@app.get("/success/{secret_key}", response_class=HTMLResponse)
async def success_page(request: Request, secret_key: str, db: Session = Depends(get_db)):
    if db_url := crud.get_db_url_by_secret_key(db, secret_key=secret_key):
        base_url = URL(get_settings().base_url)
        return templates.TemplateResponse("success.html", {
            "request": request,
            "short_url": f"{base_url}/{db_url.key}",
            "admin_url": f"{base_url}/admin/{secret_key}",
            "target_url": db_url.target_url
        })
    return templates.TemplateResponse("error.html", {
        "request": request,
        "error_message": "URL not found after creation"
    })


@app.get("/admin/{secret_key}", response_class= HTMLResponse)
async def get_url_info(request: Request, secret_key: str, db: Session = Depends(get_db)):
    if db_url := crud.get_db_url_by_secret_key(db, secret_key=secret_key):
        base_url = get_settings().base_url
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "target_url": db_url.target_url,
            "short_url": f"{base_url}/{db_url.key}",
            "clicks": db_url.clicks,
            "is_active": db_url.is_active,
            "secret_key": secret_key
        })
        
    return templates.TemplateResponse("error.html", {
        "request": request,
        "error_message": "Admin URL not found"
    })


@app.get("/{url_key}")
def forward_to_target_url(
    url_key : str,
    request: Request,
    db: Session = Depends(get_db)
    ):
    if db_url:= crud.get_db_url_by_key(db=db, url_key=url_key):
        crud.update_db_clicks(db=db, db_url=db_url)
        return RedirectResponse(db_url.target_url)
    
    else:

        return templates.TemplateResponse("error.html", {
        "request": request,
        "error_message": f"Short URL not found: {url_key}"
    })

@app.delete("/admin/{secret_key}")
def delete_url(secret_key: str, request: Request, db: Session = Depends(get_db)):

    if db_url := crud.deactivate_db_url_by_secret_key(db, secret_key = secret_key):
        message = f"Successfully deleted shortened URL for '{db_url.target_url}'"
        return {"detail": message}
    else:
        raise_not_found(request)

@app.post("/admin/{secret_key}/delete", response_class=HTMLResponse)
async def delete_url(
    secret_key: str,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        db_url = crud.deactivate_db_url_by_secret_key(db, secret_key=secret_key)
        if not db_url:
            return templates.TemplatesResponse("error.html", {
                "request": request,
                "error_message": "URL not found"
            })
        base_url = get_settings().base_url
        return templates.TemplateResponse("success.html", {
            "request": request,
            "short_url": f"{base_url}/{db_url.key}",
            "admin_url": f"{base_url}/admin/{secret_key}",
            "target_url": db_url.target_url,
            "deleted": True

        })
    except Exception as e:
        return templates.TemplatesResponse("error.html", {
            "request": request,
            "error_message": f"Failed to delete URL: {str(e)}"
        })

@app.get("/error", response_class=HTMLResponse)
async def error_page(request: Request, msg: str = "An error occurred"):
    return templates.TemplateResponse("error.html", {
        "request": request,
        "error_message": msg
    })