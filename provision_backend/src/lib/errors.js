export class ApiError extends Error {
  constructor(statusCode, code, message, details = null) {
    super(message);
    this.name = "ApiError";
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
  }
}

export function sendError(res, error) {
  if (error instanceof ApiError) {
    return res.status(error.statusCode).json({
      ok: false,
      error: error.code,
      message: error.message,
      details: error.details
    });
  }

  console.error("[provision-backend] unexpected error", error);
  return res.status(500).json({
    ok: false,
    error: "internal_server_error",
    message: "Something went wrong."
  });
}
