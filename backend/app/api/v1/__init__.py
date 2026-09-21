from fastapi import APIRouter

from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.billing import router as billing_router
from app.api.v1.departments import router as departments_router
from app.api.v1.doctors import router as doctors_router
from app.api.v1.facilities import router as facilities_router
from app.api.v1.health import router as health_router
from app.api.v1.ipd import router as ipd_router
from app.api.v1.opd import router as opd_router
from app.api.v1.patients import router as patients_router
from app.api.v1.rbac import router as rbac_router
from app.api.v1.tenants import router as tenants_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(rbac_router)
api_v1_router.include_router(tenants_router)
api_v1_router.include_router(facilities_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(patients_router)
api_v1_router.include_router(departments_router)
api_v1_router.include_router(doctors_router)
api_v1_router.include_router(opd_router)
api_v1_router.include_router(ipd_router)
api_v1_router.include_router(billing_router)
