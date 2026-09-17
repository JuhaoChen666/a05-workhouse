"""Stable business errors, without database/configuration details."""
class ExperienceError(Exception):
    def __init__(self, code, message, status=422, *, details=None):
        super().__init__(message)
        self.code, self.message, self.status, self.details = code, message, status, details


def validation_issues(error):
    return [{"field": list(item["loc"]), "code": item["type"], "message": item["msg"]}
            for item in error.errors(include_url=False, include_context=False, include_input=False)]
