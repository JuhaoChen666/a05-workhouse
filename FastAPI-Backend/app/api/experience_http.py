"""P2 route-local exception mapping, leaving legacy handlers unchanged."""
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from app.infrastructure.mapper.resume_storage_mapper import AssetNotFound, RevisionConflict
from app.services.experience_errors import ExperienceError, validation_issues


class ExperienceRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handler(request):
            try:
                return await original(request)
            except ExperienceError as error:
                detail = {"code": error.code, "message": error.message}
                if error.details is not None:
                    detail["details"] = error.details
                raise HTTPException(error.status, detail) from None
            except RequestValidationError as error:
                raise HTTPException(422, {"code":"INVALID_INPUT", "message":"Invalid request",
                    "details":[{"field": list(issue["loc"]), "code":issue["type"], "message":issue["msg"]}
                               for issue in error.errors()]}) from None
            except AssetNotFound:
                raise HTTPException(404, {"code": "NOT_FOUND", "message": "Resource unavailable"}) from None
            except RevisionConflict:
                raise HTTPException(409, {"code": "REVISION_CONFLICT", "message": "Resource has changed"}) from None
            except ValidationError as error:
                raise HTTPException(422, {"code": "INVALID_INPUT", "message": "Invalid input",
                                          "details": validation_issues(error)}) from None
            except SQLAlchemyError:
                raise HTTPException(503, {"code": "STORAGE_UNAVAILABLE", "message": "Storage operation failed; check status before retry"}) from None
            except OSError:
                raise HTTPException(409, {"code": "SOURCE_UNAVAILABLE", "message": "Source file unavailable"}) from None
        return handler


def experience_response(row):
    from app.models.resume_latex_contracts import ExperienceItemResponse
    return ExperienceItemResponse.model_validate(row, from_attributes=True)
