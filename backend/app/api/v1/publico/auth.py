from fastapi import APIRouter, Depends, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import get_settings
from app.core.deps import SessionDep, UsuarioActual
from app.core.ratelimit import limitar
from app.core.security import COOKIE_SESION
from app.schemas.admin import TokenOut, UsuarioOut
from app.services import auth

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post(
    "/login",
    response_model=TokenOut,
    summary="Iniciar sesión (personal)",
    description=(
        "Devuelve el token y además lo deja en una cookie httpOnly (`em_session`) para el panel web. "
        "Máximo 10 intentos cada 5 minutos por IP."
    ),
    dependencies=[Depends(limitar("login", 10, 300))],
)
async def login(response: Response, session: SessionDep, form: OAuth2PasswordRequestForm = Depends()):
    _, token, expira_en = await auth.login(session, form.username, form.password)
    settings = get_settings()
    response.set_cookie(
        COOKIE_SESION,
        token,
        max_age=expira_en,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/api",
    )
    response.headers["Cache-Control"] = "no-store"
    return {"access_token": token, "expires_in": expira_en}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Cerrar sesión")
async def logout(response: Response):
    settings = get_settings()
    response.delete_cookie(COOKIE_SESION, path="/api", secure=settings.cookie_secure, httponly=True, samesite="strict")


@router.get("/me", response_model=UsuarioOut, summary="Usuario de la sesión actual")
async def me(usuario: UsuarioActual):
    return usuario
