"""
FastAPI Backend API for MPF-PD Dashboard (Phase 8).

Wraps src.pipeline.run_mpf_pipeline and exposes:
  - GET  /api/health   : Health status & model artifact verification
  - POST /api/analyze  : Multimodal screening analysis with multipart file uploads

RESEARCH PROTOTYPE ONLY — NOT FOR CLINICAL DIAGNOSIS.
Privacy: Temporary files are scrubbed immediately after processing.
"""

import json
import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure project root is on sys.path
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.pipeline import run_mpf_pipeline
from dashboard.api.schemas import (
    AnalysisResponse,
    HealthResponse,
)

logger = logging.getLogger("mpf.api")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="MPF-PD Multimodal Risk Screening API",
    description="Research prototype API for prodromal Parkinson's disease risk screening. Not for clinical diagnosis.",
    version="0.8.0",
)

# Enable CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local development across Vite ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Check readiness of pipeline and model artifacts."""
    artifacts = {
        "fusion_classifier": Path("models/fusion/classifier.joblib").exists(),
        "fusion_encoder": Path("models/fusion/fusion_encoder.pt").exists(),
        "fusion_preprocessor": Path("models/fusion/preprocessor.joblib").exists(),
        "voice_model": Path("models/voice/model.joblib").exists(),
        "motor_model": Path("models/motor/model.joblib").exists(),
        "olfactory_model": Path("models/olfactory/model.joblib").exists(),
        "rbd_model": Path("models/rbd/model.joblib").exists(),
    }

    all_ready = all(artifacts.values())
    status_str = "ok" if all_ready else "degraded"
    msg = (
        "All model artifacts loaded and ready for multimodal inference."
        if all_ready
        else "Some model artifacts missing. Run training pipelines."
    )

    return HealthResponse(
        status=status_str,
        version="0.8.0",
        models_loaded=artifacts,
        message=msg,
    )


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_multimodal(
    request: Request,
    payload: Optional[str] = Form(None),
    voice_file: Optional[UploadFile] = File(None),
    motor_file: Optional[UploadFile] = File(None),
    retina_file: Optional[UploadFile] = File(None),
) -> Any:
    """
    Execute multimodal analysis.

    Accepts either:
      1. Multipart form with 'payload' (JSON string containing participant & tabular data)
         plus optional file uploads ('voice_file', 'motor_file', 'retina_file').
      2. Direct application/json body (when no files are uploaded).
    """
    temp_dir = tempfile.mkdtemp(prefix="mpf_upload_")
    try:
        inputs: Dict[str, Any] = {}

        # 1. Parse payload if JSON body was sent directly
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                inputs = await request.json()
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid JSON request body: {str(e)}",
                )
        elif payload:
            try:
                inputs = json.loads(payload)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid JSON in form payload: {str(e)}",
                )

        # 2. Save uploaded files to secure temporary directory and assign to inputs
        if voice_file is not None and voice_file.filename:
            v_path = os.path.join(temp_dir, f"voice_{Path(voice_file.filename).name}")
            with open(v_path, "wb") as f:
                content = await voice_file.read()
                f.write(content)
            if "voice" not in inputs:
                inputs["voice"] = {"available": True}
            inputs["voice"]["audio_file"] = v_path

        if motor_file is not None and motor_file.filename:
            m_path = os.path.join(temp_dir, f"motor_{Path(motor_file.filename).name}")
            with open(m_path, "wb") as f:
                content = await motor_file.read()
                f.write(content)
            if "motor" not in inputs:
                inputs["motor"] = {"available": True}
            inputs["motor"]["file_path"] = m_path

        if retina_file is not None and retina_file.filename:
            r_path = os.path.join(temp_dir, f"retina_{Path(retina_file.filename).name}")
            with open(r_path, "wb") as f:
                content = await retina_file.read()
                f.write(content)
            if "retina" not in inputs:
                inputs["retina"] = {"available": True}
            inputs["retina"]["image_path"] = r_path

        # 3. Run multimodal pipeline
        result = run_mpf_pipeline(inputs)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Pipeline execution failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline execution encountered an error: {str(e)}",
        )
    finally:
        # Clean up temporary directory immediately to protect privacy
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("dashboard.api.main:app", host="0.0.0.0", port=8000, reload=True)
